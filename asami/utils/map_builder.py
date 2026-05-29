"""
Утилита построения интерактивных Folium-карт с choropleth-слоем.

Создаёт карты Москвы с тепловой раскраской административных округов
по плотности МО и маркерами конкретных медицинских организаций.
"""

import json
import logging
from typing import List, Optional

import folium
import pandas as pd
from folium.plugins import MarkerCluster

logger = logging.getLogger(__name__)

# Цветовые схемы для статусов округов
COLOR_GOOD    = "#16A34A"   # зелёный — плотность выше порога
COLOR_WARN    = "#D97706"   # жёлтый — близко к порогу
COLOR_BAD     = "#DC2626"   # красный — ниже порога (белое пятно)
COLOR_NEUTRAL = "#64748B"   # серый — нейтральный

# Иконки по типам МО
MO_ICONS: dict[str, tuple[str, str]] = {
    "hospital":    ("red",    "plus-sign"),
    "polyclinic":  ("blue",   "user-md"),
    "ambulatory":  ("green",  "home"),
    "specialized": ("purple", "star"),
}


def _district_color(density: float, threshold: float) -> str:
    """Возвращает цвет заливки округа в зависимости от density и порога."""
    if density >= threshold * 1.5:
        return COLOR_GOOD
    if density >= threshold:
        return "#86EFAC"   # светло-зелёный
    if density >= threshold * 0.7:
        return "#FCD34D"   # жёлтый
    if density >= threshold * 0.4:
        return "#F97316"   # оранжевый
    return COLOR_BAD


def build_choropleth_map(
    districts_df: pd.DataFrame,
    threshold: float = 3.0,
    center: Optional[List[float]] = None,
    zoom: int = 10,
) -> folium.Map:
    """
    Строит choropleth-карту плотности МО по округам Москвы.

    Каждый округ отображается как кружок (CircleMarker) с цветом,
    зависящим от плотности МО. При клике показывается popup с метриками.

    Args:
        districts_df: DataFrame с колонками name, lat, lon, density,
                      population, total_mo, accessibility_score.
        threshold: Порог плотности для цветовой схемы.
        center: Центр карты [lat, lon].
        zoom: Начальный масштаб.

    Returns:
        Объект folium.Map с добавленными слоями.
    """
    if center is None:
        center = [55.7558, 37.6173]

    m = folium.Map(
        location=center,
        zoom_start=zoom,
        tiles="CartoDB positron",
        control_scale=True,
    )

    logger.info("build_choropleth_map: строю карту для %d округов", len(districts_df))

    for _, row in districts_df.iterrows():
        density   = float(row.get("density", 0))
        lat       = float(row.get("lat", center[0]))
        lon       = float(row.get("lon", center[1]))
        name      = str(row.get("name", "—"))
        full_name = str(row.get("full_name", name))
        pop       = int(row.get("population", 0))
        total_mo  = int(row.get("total_mo", 0))
        acc       = float(row.get("accessibility_score", 0))

        color = _district_color(density, threshold)

        # Popup с деталями округа
        popup_html = f"""
        <div style="font-family:Arial,sans-serif;min-width:200px;">
          <h4 style="margin:0 0 8px;color:#1B3A6B;font-size:14px;">🏥 {full_name}</h4>
          <table style="width:100%;font-size:12px;border-collapse:collapse;">
            <tr><td style="color:#64748B;padding:3px 0;">Население</td>
                <td style="font-weight:700;text-align:right;">{pop:,} чел.</td></tr>
            <tr><td style="color:#64748B;padding:3px 0;">Всего МО</td>
                <td style="font-weight:700;text-align:right;">{total_mo} шт.</td></tr>
            <tr><td style="color:#64748B;padding:3px 0;">Плотность МО</td>
                <td style="font-weight:700;text-align:right;color:{color};">{density:.2f} / 10 000</td></tr>
            <tr><td style="color:#64748B;padding:3px 0;">Доступность</td>
                <td style="font-weight:700;text-align:right;">{acc:.2%}</td></tr>
          </table>
          <div style="margin-top:8px;padding:4px 8px;border-radius:4px;
                      background:{'#F0FDF4' if density >= threshold else '#FEF2F2'};
                      color:{'#15803D' if density >= threshold else '#B91C1C'};
                      font-size:11px;font-weight:600;">
            {'✓ Выше порога' if density >= threshold else '⚠ Ниже порога'} ({threshold:.1f})
          </div>
        </div>
        """

        # Размер кружка пропорционален плотности
        radius = max(12, min(50, density * 8))

        folium.CircleMarker(
            location=[lat, lon],
            radius=radius,
            color="white",
            weight=2,
            fill=True,
            fill_color=color,
            fill_opacity=0.75,
            popup=folium.Popup(popup_html, max_width=260),
            tooltip=f"{name}: {density:.2f} МО/10 000",
        ).add_to(m)

        # Подпись округа
        folium.map.Marker(
            location=[lat, lon],
            icon=folium.DivIcon(
                html=f'<div style="font-size:9px;font-weight:700;color:white;'
                     f'text-shadow:0 1px 2px rgba(0,0,0,0.8);'
                     f'text-align:center;width:60px;margin-left:-30px;">{name}</div>',
                icon_size=(60, 20),
                icon_anchor=(30, 10),
            ),
        ).add_to(m)

    # Легенда
    legend_html = f"""
    <div style="position:fixed;bottom:30px;left:30px;z-index:1000;
                background:white;padding:10px 14px;border-radius:8px;
                border:1px solid #E2E8F0;box-shadow:0 2px 8px rgba(0,0,0,0.15);
                font-family:Arial,sans-serif;font-size:11px;">
      <b style="color:#1B3A6B;">Плотность МО / 10 000 жит.</b><br>
      <div style="margin-top:6px;">
        <span style="color:{COLOR_GOOD};">●</span> ≥ {threshold*1.5:.1f} — высокая<br>
        <span style="color:#86EFAC;">●</span> ≥ {threshold:.1f} — норма<br>
        <span style="color:#FCD34D;">●</span> ≥ {threshold*0.7:.1f} — внимание<br>
        <span style="color:#F97316;">●</span> ≥ {threshold*0.4:.1f} — дефицит<br>
        <span style="color:{COLOR_BAD};">●</span> &lt; {threshold*0.4:.1f} — критично<br>
      </div>
      <div style="margin-top:4px;font-size:10px;color:#94A3B8;">Порог: {threshold:.1f}</div>
    </div>
    """
    m.get_root().html.add_child(folium.Element(legend_html))

    return m


def add_mo_markers(
    m: folium.Map,
    mo_df: pd.DataFrame,
    cluster: bool = True,
) -> folium.Map:
    """
    Добавляет маркеры МО на карту.

    Args:
        m: Существующая Folium-карта.
        mo_df: DataFrame с колонками lat, lon, name, type, address.
        cluster: Если True — группирует маркеры в кластеры.

    Returns:
        Карта с добавленными маркерами.
    """
    logger.info("add_mo_markers: добавляю %d маркеров (cluster=%s)", len(mo_df), cluster)

    if cluster:
        layer = MarkerCluster(name="Медицинские организации")
    else:
        layer = folium.FeatureGroup(name="Медицинские организации")

    for _, row in mo_df.iterrows():
        lat  = float(row.get("lat", 55.7558))
        lon  = float(row.get("lon", 37.6173))
        name = str(row.get("name", "МО"))
        mo_type = str(row.get("type", "polyclinic"))
        address = str(row.get("address", "—"))
        source  = str(row.get("source", "—"))
        score   = float(row.get("confidence_score", 0.8))

        color, icon = MO_ICONS.get(mo_type, ("gray", "info-sign"))

        popup_html = f"""
        <div style="font-family:Arial,sans-serif;min-width:180px;font-size:12px;">
          <b style="color:#1B3A6B;">{name}</b><br>
          <span style="color:#64748B;">{address}</span><br>
          <hr style="margin:4px 0;border:none;border-top:1px solid #E2E8F0;">
          <span style="color:#64748B;">Источник: {source}</span><br>
          <span style="color:#64748B;">Достоверность: {score:.0%}</span>
        </div>
        """

        folium.Marker(
            location=[lat, lon],
            icon=folium.Icon(color=color, icon=icon, prefix="glyphicon"),
            popup=folium.Popup(popup_html, max_width=220),
            tooltip=name,
        ).add_to(layer)

    layer.add_to(m)
    folium.LayerControl().add_to(m)
    return m


def build_white_spots_map(
    districts_df: pd.DataFrame,
    threshold: float,
    center: Optional[List[float]] = None,
    zoom: int = 10,
) -> folium.Map:
    """
    Строит карту «белых пятен»: красные округа ниже порога, серые — в норме.

    Args:
        districts_df: DataFrame с колонками name, lat, lon, density, population.
        threshold: Пороговое значение плотности.
        center: Центр карты [lat, lon].
        zoom: Начальный масштаб.

    Returns:
        Folium-карта с выделенными проблемными округами.
    """
    if center is None:
        center = [55.7558, 37.6173]

    m = folium.Map(
        location=center,
        zoom_start=zoom,
        tiles="CartoDB positron",
        control_scale=True,
    )

    logger.info("build_white_spots_map: порог=%.1f, %d округов", threshold, len(districts_df))

    for _, row in districts_df.iterrows():
        density  = float(row.get("density", 0))
        lat      = float(row.get("lat", center[0]))
        lon      = float(row.get("lon", center[1]))
        name     = str(row.get("name", "—"))
        full_name = str(row.get("full_name", name))
        pop      = int(row.get("population", 0))
        total_mo = int(row.get("total_mo", 0))

        is_problem = density < threshold
        fill_color = COLOR_BAD if is_problem else COLOR_NEUTRAL
        fill_opacity = 0.80 if is_problem else 0.35

        deficit = max(0, int(threshold * pop / 10_000 - total_mo))

        popup_html = f"""
        <div style="font-family:Arial,sans-serif;min-width:200px;">
          <h4 style="margin:0 0 6px;color:{'#B91C1C' if is_problem else '#1B3A6B'};font-size:13px;">
            {'⚠ ' if is_problem else '✓ '}{full_name}
          </h4>
          {'<div style="background:#FEF2F2;padding:3px 8px;border-radius:4px;margin-bottom:6px;'
           'font-size:11px;color:#B91C1C;font-weight:700;">Ниже порога: ' + f'{density:.2f} &lt; {threshold:.1f}</div>'
           if is_problem else ''}
          <div style="font-size:12px;">
            Плотность МО: <b style="color:{'#B91C1C' if is_problem else '#15803D'};">{density:.2f}</b><br>
            Всего МО: <b>{total_mo}</b><br>
            Население: <b>{pop:,}</b><br>
            {'Дефицит МО: <b style="color:#B91C1C;">' + str(deficit) + ' шт.</b>' if is_problem else ''}
          </div>
        </div>
        """

        folium.CircleMarker(
            location=[lat, lon],
            radius=max(14, min(50, density * 7 + 5)),
            color="white" if is_problem else "#94A3B8",
            weight=3 if is_problem else 1,
            fill=True,
            fill_color=fill_color,
            fill_opacity=fill_opacity,
            popup=folium.Popup(popup_html, max_width=250),
            tooltip=f"{name}: {density:.2f}" + (" ⚠" if is_problem else " ✓"),
        ).add_to(m)

        folium.map.Marker(
            location=[lat, lon],
            icon=folium.DivIcon(
                html=f'<div style="font-size:8px;font-weight:700;'
                     f'color:white;text-shadow:0 1px 2px rgba(0,0,0,0.9);'
                     f'text-align:center;width:60px;margin-left:-30px;">'
                     f'{name}<br>{"⚠" if is_problem else "✓"}</div>',
                icon_size=(60, 24),
                icon_anchor=(30, 12),
            ),
        ).add_to(m)

    # Легенда
    problem_count = int((districts_df["density"] < threshold).sum())
    legend_html = f"""
    <div style="position:fixed;bottom:30px;left:30px;z-index:1000;
                background:white;padding:10px 14px;border-radius:8px;
                border:1px solid #E2E8F0;box-shadow:0 2px 8px rgba(0,0,0,0.15);
                font-family:Arial,sans-serif;font-size:11px;">
      <b style="color:#1B3A6B;">Карта «Белых пятен»</b><br>
      <div style="margin-top:6px;">
        <span style="color:{COLOR_BAD};">●</span> Ниже порога {threshold:.1f} — {problem_count} округов<br>
        <span style="color:{COLOR_NEUTRAL};">●</span> В норме — {len(districts_df) - problem_count} округов
      </div>
    </div>
    """
    m.get_root().html.add_child(folium.Element(legend_html))

    return m
