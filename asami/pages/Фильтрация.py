"""
Страница «Фильтрация по типу МО» системы АСАМИ.

Позволяет фильтровать медицинские организации по типу,
отображает карту с маркерами и pie chart распределения.
"""

import logging

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from streamlit_folium import st_folium

from utils.map_builder import build_choropleth_map, add_mo_markers

logger = logging.getLogger(__name__)

# Справочник типов МО (русские названия)
TYPE_LABELS: dict[str, str] = {
    "all":         "Все типы",
    "hospital":    "Больницы",
    "polyclinic":  "Поликлиники",
    "ambulatory":  "Амбулатории",
    "specialized": "Специализированные центры",
}

# Цветовая палитра для типов (строгая, без кричащих тонов)
TYPE_COLORS: dict[str, str] = {
    "hospital":    "#1B3A6B",
    "polyclinic":  "#2563EB",
    "ambulatory":  "#15803D",
    "specialized": "#6D28D9",
}


def render(
    districts_df: pd.DataFrame,
    mo_df: pd.DataFrame,
    threshold: float,
) -> None:
    """
    Рендерит страницу фильтрации по типу МО.

    Args:
        districts_df: DataFrame с метриками по округам.
        mo_df: DataFrame со всеми МО.
        threshold: Пороговое значение плотности из sidebar.
    """
    logger.info("Рендеринг страницы фильтрации: %d МО", len(mo_df))

    # ── Выбор типа МО (radio без эмодзи) ─────────────────────────────────────
    type_keys   = list(TYPE_LABELS.keys())
    type_names  = list(TYPE_LABELS.values())

    selected_name = st.radio(
        "Тип медицинской организации",
        options=type_names,
        horizontal=True,
        key="filter_type_radio",
    )
    selected_type = type_keys[type_names.index(selected_name)]

    # Фильтрация
    filtered_mo = (
        mo_df.copy() if selected_type == "all"
        else mo_df[mo_df["type"] == selected_type].copy()
    )

    total_all    = len(mo_df)
    total_shown  = len(filtered_mo)

    st.markdown("<div style='margin-top:10px;'></div>", unsafe_allow_html=True)

    # ── KPI ───────────────────────────────────────────────────────────────────
    k1, k2, k3, k4 = st.columns(4)

    # Округа без МО выбранного типа
    if selected_type != "all":
        have_type     = set(filtered_mo["district"].unique())
        without_count = int((~districts_df["name"].isin(have_type)).sum())
    else:
        without_count = 0

    # Средняя плотность по выбранному типу
    if selected_type != "all" and total_shown > 0:
        cnt = filtered_mo.groupby("district").size().reset_index(name="n")
        tmp = districts_df.merge(cnt, left_on="name", right_on="district", how="left")
        tmp["n"] = tmp["n"].fillna(0)
        avg_type_density = round(float((tmp["n"] / (tmp["population"] / 10_000)).mean()), 2)
    else:
        avg_type_density = round(float(districts_df["density"].mean()), 2)

    with k1:
        st.markdown(
            f"""<div class="kpi-card kpi-blue">
              <div class="kpi-label">{selected_name}</div>
              <div class="kpi-value" style="color:#1D4ED8;">{total_shown}</div>
              <div class="kpi-sub">из {total_all} МО в городе</div>
            </div>""",
            unsafe_allow_html=True,
        )
    with k2:
        st.markdown(
            f"""<div class="kpi-card kpi-green">
              <div class="kpi-label">Средняя плотность</div>
              <div class="kpi-value" style="color:#15803D;">{avg_type_density}</div>
              <div class="kpi-sub">МО / 10 000 жит.</div>
            </div>""",
            unsafe_allow_html=True,
        )
    with k3:
        src_count = filtered_mo["source"].nunique() if total_shown else 0
        st.markdown(
            f"""<div class="kpi-card kpi-orange">
              <div class="kpi-label">Источников данных</div>
              <div class="kpi-value" style="color:#B45309;">{src_count}</div>
              <div class="kpi-sub">официальный / OSM</div>
            </div>""",
            unsafe_allow_html=True,
        )
    with k4:
        st.markdown(
            f"""<div class="kpi-card kpi-red">
              <div class="kpi-label">Округов без {selected_name.lower()}</div>
              <div class="kpi-value" style="color:#B91C1C;">{without_count}</div>
              <div class="kpi-sub">из {len(districts_df)}</div>
            </div>""",
            unsafe_allow_html=True,
        )

    st.markdown("<div style='margin-top:14px;'></div>", unsafe_allow_html=True)

    # ── Карта + диаграмма ─────────────────────────────────────────────────────
    map_col, pie_col = st.columns([3, 2])

    with map_col:
        st.markdown(
            f'<div class="section-title">Карта: {selected_name}</div>',
            unsafe_allow_html=True,
        )
        try:
            folium_map = build_choropleth_map(districts_df, threshold=threshold)
            if total_shown > 0:
                folium_map = add_mo_markers(folium_map, filtered_mo, cluster=True)
            st_folium(
                folium_map, height=390,
                use_container_width=True, returned_objects=[],
            )
        except Exception as exc:
            logger.error("Ошибка карты (фильтрация): %s", exc)
            st.error(f"Ошибка карты: {exc}")

    with pie_col:
        st.markdown(
            '<div class="section-title">Распределение МО по типам</div>',
            unsafe_allow_html=True,
        )
        _render_donut(mo_df, selected_type)

    st.markdown("<div style='margin-top:4px;'></div>", unsafe_allow_html=True)

    # ── Таблица МО ───────────────────────────────────────────────────────────
    st.markdown(
        f'<div class="section-title">Список МО — {selected_name}</div>',
        unsafe_allow_html=True,
    )

    display_cols = {
        "name":             "Название",
        "type":             "Тип",
        "district":         "Округ",
        "address":          "Адрес",
        "source":           "Источник",
        "confidence_score": "Достоверность",
    }

    table_df = filtered_mo[
        [c for c in display_cols if c in filtered_mo.columns]
    ].copy()
    table_df.rename(columns=display_cols, inplace=True)

    if "Тип" in table_df.columns:
        table_df["Тип"] = table_df["Тип"].map(TYPE_LABELS).fillna(table_df["Тип"])
    if "Достоверность" in table_df.columns:
        table_df["Достоверность"] = table_df["Достоверность"].map("{:.0%}".format)

    st.dataframe(table_df, use_container_width=True, hide_index=True, height=260)
    st.caption(f"Показано {total_shown} из {total_all} МО")


def _render_donut(mo_df: pd.DataFrame, selected_type: str) -> None:
    """
    Рендерит donut-диаграмму распределения МО по типам.

    Строгий дизайн: тёмные корпоративные цвета, читаемые подписи.

    Args:
        mo_df: Полный DataFrame МО.
        selected_type: Выбранный тип для выделения сегмента.
    """
    try:
        counts = mo_df["type"].value_counts().reset_index()
        counts.columns = ["type", "count"]
        counts["label"] = counts["type"].map(TYPE_LABELS).fillna(counts["type"])
        counts["pct"]   = (counts["count"] / counts["count"].sum() * 100).round(1)

        colors = [TYPE_COLORS.get(t, "#94A3B8") for t in counts["type"]]
        pulls  = [0.06 if t == selected_type else 0 for t in counts["type"]]

        fig = go.Figure(
            go.Pie(
                labels=counts["label"],
                values=counts["count"],
                marker=dict(
                    colors=colors,
                    line=dict(color="white", width=2),
                ),
                hole=0.52,
                pull=pulls,
                textinfo="percent",
                textfont=dict(size=13, color="white", family="Arial"),
                hovertemplate=(
                    "<b>%{label}</b><br>"
                    "Количество: %{value}<br>"
                    "Доля: %{percent}<extra></extra>"
                ),
                direction="clockwise",
            )
        )

        # Подпись в центре кольца
        total = int(counts["count"].sum())
        fig.add_annotation(
            text=f"<b>{total}</b><br><span style='font-size:10px'>всего МО</span>",
            x=0.5, y=0.5,
            font=dict(size=14, color="#1B3A6B", family="Arial"),
            showarrow=False,
            align="center",
        )

        fig.update_layout(
            height=340,
            margin=dict(l=10, r=10, t=16, b=10),
            paper_bgcolor="white",
            showlegend=True,
            legend=dict(
                orientation="v",
                x=1.02, y=0.5,
                font=dict(size=11, color="#334155"),
                itemsizing="constant",
            ),
            font=dict(family="Arial, sans-serif"),
        )

        st.plotly_chart(fig, use_container_width=True)

    except Exception as exc:
        logger.error("Ошибка donut chart: %s", exc)
        st.error(f"Ошибка диаграммы: {exc}")
