"""
Страница «Белые пятна» системы АСАМИ.

Выявляет административные округа с дефицитом медицинской инфраструктуры
(density ниже заданного порога), отображает карту и таблицу дефицита,
позволяет экспортировать отчёт в CSV.
"""

import io
import logging

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from streamlit_folium import st_folium

from utils.map_builder import build_white_spots_map

logger = logging.getLogger(__name__)

RECOMMENDATIONS: dict[str, str] = {
    "ЦАО":   "Высокая плотность застройки — целесообразно открытие мобильных пунктов МО.",
    "САО":   "Необходимо расширение сети амбулаторий в северных районах.",
    "СВАО":  "Требуется строительство 2–3 поликлиник в новых жилых кварталах.",
    "ВАО":   "Рекомендуется реконструкция существующих МО и открытие специализированных центров.",
    "ЮВАО":  "Приоритет: открытие поликлиник в районах Люблино и Марьино.",
    "ЮАО":   "Необходимо размещение не менее 4 новых МО в районах Чертаново и Бирюлёво.",
    "ЮЗАО":  "Рекомендуется развитие телемедицины как дополнение к стационарной сети.",
    "ЗАО":   "Требуется открытие 2 амбулаторий в районах Можайский и Фили-Давыдково.",
    "СЗАО":  "Необходимо размещение МО в новых районах Митино и Строгино.",
    "ЗеАО":  "Расширение существующих МО — приоритет перед строительством новых.",
    "НАО":   "Срочно требуется открытие поликлиники в районе Щербинка.",
    "ТиНАО": "Острый дефицит МО. Необходимо открытие 3+ объектов в г. Троицк и посёлках.",
}
DEFAULT_REC = (
    "Рекомендуется провести детальное обследование территории "
    "и разработать план размещения новых МО с учётом транспортной доступности."
)


def render(districts_df: pd.DataFrame, threshold: float) -> None:
    """
    Рендерит страницу «Белые пятна».

    Args:
        districts_df: DataFrame с метриками по округам.
        threshold: Пороговое значение плотности (синхронизировано с sidebar).
    """
    logger.info(
        "Рендеринг страницы «Белые пятна»: порог=%.1f, округов=%d",
        threshold, len(districts_df),
    )

    # ── Локальный ползунок (синхронизирован с sidebar) ────────────────────────
    local_threshold = st.slider(
        "Пороговое значение плотности МО (МО / 10 000 жит.)",
        min_value=0.5,
        max_value=5.0,
        value=threshold,
        step=0.1,
        key="ws_threshold_slider",
        help="Округа ниже этого значения считаются «белыми пятнами»",
    )
    thr = local_threshold

    # Разделение на проблемные и нормальные
    problem_df = districts_df[districts_df["density"] < thr].copy()
    normal_df  = districts_df[districts_df["density"] >= thr].copy()
    p_count    = len(problem_df)
    n_count    = len(normal_df)
    aff_pop    = int(problem_df["population"].sum())

    # ── KPI ───────────────────────────────────────────────────────────────────
    k1, k2, k3, k4 = st.columns(4)

    total_deficit = int(
        (thr * problem_df["population"] / 10_000 - problem_df["total_mo"])
        .clip(lower=0).sum()
    ) if p_count > 0 else 0

    with k1:
        st.markdown(
            f"""<div class="kpi-card kpi-red">
              <div class="kpi-label">«Белых пятен»</div>
              <div class="kpi-value" style="color:#B91C1C;">{p_count}</div>
              <div class="kpi-sub">density &lt; {thr:.1f}</div>
            </div>""",
            unsafe_allow_html=True,
        )
    with k2:
        st.markdown(
            f"""<div class="kpi-card kpi-green">
              <div class="kpi-label">Округов в норме</div>
              <div class="kpi-value" style="color:#15803D;">{n_count}</div>
              <div class="kpi-sub">density ≥ {thr:.1f}</div>
            </div>""",
            unsafe_allow_html=True,
        )
    with k3:
        pop_str = (
            f"{aff_pop / 1_000_000:.2f} млн"
            if aff_pop >= 1_000_000
            else f"{aff_pop / 1_000:.0f} тыс."
        )
        st.markdown(
            f"""<div class="kpi-card kpi-orange">
              <div class="kpi-label">Население в дефицитных</div>
              <div class="kpi-value" style="color:#B45309;">{pop_str}</div>
              <div class="kpi-sub">в проблемных округах</div>
            </div>""",
            unsafe_allow_html=True,
        )
    with k4:
        st.markdown(
            f"""<div class="kpi-card kpi-blue">
              <div class="kpi-label">Требуется открыть МО</div>
              <div class="kpi-value" style="color:#1D4ED8;">{total_deficit}</div>
              <div class="kpi-sub">для достижения порога</div>
            </div>""",
            unsafe_allow_html=True,
        )

    st.markdown("<div style='margin-top:14px;'></div>", unsafe_allow_html=True)

    # ── Карта + список проблемных округов ────────────────────────────────────
    map_col, list_col = st.columns([3, 2])

    with map_col:
        st.markdown(
            f'<div class="section-title">'
            f'Карта «белых пятен» — порог {thr:.1f} МО / 10 000</div>',
            unsafe_allow_html=True,
        )
        try:
            ws_map = build_white_spots_map(districts_df, threshold=thr)
            st_folium(ws_map, height=420, use_container_width=True, returned_objects=[])
        except Exception as exc:
            logger.error("Ошибка карты (белые пятна): %s", exc)
            st.error(f"Ошибка карты: {exc}")

    with list_col:
        st.markdown(
            '<div class="section-title">Проблемные округа</div>',
            unsafe_allow_html=True,
        )

        if p_count == 0:
            st.success(
                f"Все {len(districts_df)} округов соответствуют "
                f"пороговому значению {thr:.1f}. Дефицита не выявлено."
            )
        else:
            problem_sorted = problem_df.sort_values("density")
            for _, row in problem_sorted.iterrows():
                name    = str(row["name"])
                density = float(row["density"])
                pop     = int(row["population"])
                mo_now  = int(row["total_mo"])
                deficit = max(0, int(thr * pop / 10_000 - mo_now))
                rec     = RECOMMENDATIONS.get(name, DEFAULT_REC)

                with st.expander(
                    f"{name}  —  {density:.2f} МО/10 000  (дефицит: {deficit} МО)"
                ):
                    ca, cb = st.columns(2)
                    with ca:
                        st.metric("Текущая плотность", f"{density:.2f}")
                        st.metric("Всего МО", mo_now)
                    with cb:
                        st.metric("Порог", f"{thr:.1f}")
                        st.metric("Нужно добавить", deficit)
                    st.info(rec)

            st.markdown(
                f'<div style="margin-top:8px;padding:8px 12px;background:#F0FDF4;'
                f'border-left:3px solid #15803D;border-radius:3px;'
                f'font-size:12px;color:#15803D;font-weight:600;">'
                f'В норме: {n_count} из {len(districts_df)} округов</div>',
                unsafe_allow_html=True,
            )

    st.markdown("<div style='margin-top:4px;'></div>", unsafe_allow_html=True)

    # ── Сводная таблица дефицита ──────────────────────────────────────────────
    st.markdown(
        '<div class="section-title">Сводная таблица дефицита МО</div>',
        unsafe_allow_html=True,
    )

    deficit_df = districts_df[
        ["name", "full_name", "population", "density", "total_mo"]
    ].copy()
    deficit_df["Дефицит МО"] = (
        thr * deficit_df["population"] / 10_000 - deficit_df["total_mo"]
    ).clip(lower=0).astype(int)
    deficit_df["Статус"] = deficit_df["density"].apply(
        lambda d: "Дефицит" if d < thr else "Норма"
    )
    deficit_df = deficit_df.sort_values("density")

    display_df = deficit_df.rename(columns={
        "name":       "Округ",
        "full_name":  "Полное название",
        "population": "Население",
        "density":    "Плотность",
        "total_mo":   "МО сейчас",
    })[["Округ", "Полное название", "Население", "Плотность",
        "МО сейчас", "Дефицит МО", "Статус"]]

    display_df["Плотность"]  = display_df["Плотность"].map("{:.2f}".format)
    display_df["Население"]  = display_df["Население"].map("{:,}".format)

    st.dataframe(display_df, use_container_width=True, hide_index=True, height=340)

    # ── Диаграмма дефицита (только проблемные) ──────────────────────────────
    if p_count > 0:
        st.markdown(
            '<div class="section-title" style="margin-top:10px;">'
            'Дефицит МО по проблемным округам</div>',
            unsafe_allow_html=True,
        )
        _render_deficit_chart(deficit_df[deficit_df["Дефицит МО"] > 0], thr)

    # ── Экспорт ───────────────────────────────────────────────────────────────
    st.markdown(
        '<div class="section-title" style="margin-top:10px;">Экспорт отчёта</div>',
        unsafe_allow_html=True,
    )

    meta = (
        f"# Отчёт АСАМИ — «Белые пятна»\n"
        f"# Дата: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')}\n"
        f"# Порог: {thr:.1f} МО / 10 000 жит.\n"
        f"# Проблемных округов: {p_count}\n\n"
    )
    buf = io.StringIO()
    buf.write(meta)
    display_df.to_csv(buf, index=False, encoding="utf-8-sig")

    st.download_button(
        label="Скачать отчёт (CSV)",
        data=buf.getvalue().encode("utf-8-sig"),
        file_name=f"asami_white_spots_{pd.Timestamp.now().strftime('%Y%m%d')}.csv",
        mime="text/csv",
        use_container_width=True,
    )
    st.caption(
        f"Файл содержит данные по всем {len(districts_df)} округам. "
        f"Выделены {p_count} округов с дефицитом МО."
    )


def _render_deficit_chart(df: pd.DataFrame, threshold: float) -> None:
    """
    Горизонтальный bar chart дефицита МО по проблемным округам.

    Цвет насыщенности зависит от величины дефицита — чем больше, тем темнее.

    Args:
        df: DataFrame с колонками 'Округ' / 'name' и 'Дефицит МО'.
        threshold: Используется для подписи оси.
    """
    chart = df.sort_values("Дефицит МО").copy()

    # Определяем имя колонки округа
    name_col = "Округ" if "Округ" in chart.columns else "name"

    max_def = int(chart["Дефицит МО"].max())

    # Градиент красного: маленький дефицит — светлее, большой — темнее
    def _red(val: int) -> str:
        ratio = val / max_def if max_def > 0 else 0
        r = int(185 + (180 - 185) * ratio)   # 185 → 140
        g = int(28  + (0   - 28 ) * ratio)    # 28  → 0
        b = int(28  + (0   - 28 ) * ratio)    # 28  → 0
        return f"rgb({r},{g},{b})"

    colors = [_red(int(v)) for v in chart["Дефицит МО"]]

    fig = go.Figure(
        go.Bar(
            x=chart["Дефицит МО"],
            y=chart[name_col],
            orientation="h",
            marker=dict(
                color=colors,
                line=dict(color="rgba(0,0,0,0.07)", width=0.5),
            ),
            text=chart["Дефицит МО"],
            textposition="outside",
            textfont=dict(size=12, color="#1E293B", family="Arial"),
            cliponaxis=False,
            hovertemplate=(
                "<b>%{y}</b><br>"
                "Требуется открыть: <b>%{x}</b> МО<extra></extra>"
            ),
            width=0.6,
        )
    )

    fig.update_layout(
        xaxis_title=f"МО для открытия (порог {threshold:.1f})",
        yaxis_title=None,
        height=max(220, len(chart) * 52),
        margin=dict(l=0, r=60, t=10, b=44),
        plot_bgcolor="white",
        paper_bgcolor="white",
        xaxis=dict(
            gridcolor="#F1F5F9",
            gridwidth=1,
            showline=True,
            linecolor="#E2E8F0",
            tickfont=dict(size=11, color="#475569"),
            title_font=dict(size=11, color="#475569"),
            zeroline=False,
        ),
        yaxis=dict(
            tickfont=dict(size=12, color="#1E293B"),
            showgrid=False,
        ),
        font=dict(family="Arial, sans-serif"),
        bargap=0.35,
    )

    st.plotly_chart(fig, use_container_width=True)
