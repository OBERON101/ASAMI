"""
Страница «Мониторинг общей ситуации» системы АСАМИ.

Отображает KPI-карточки, интерактивную choropleth-карту,
рейтинговую таблицу округов и горизонтальный bar chart.
"""

import logging

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from streamlit_folium import st_folium

from utils.map_builder import build_choropleth_map, add_mo_markers

logger = logging.getLogger(__name__)


def _status_label(density: float, threshold: float) -> str:
    """Возвращает текстовый статус без эмодзи."""
    if density >= threshold * 1.3:
        return "Норма"
    if density >= threshold:
        return "Внимание"
    return "Дефицит"


def _bar_color(density: float, threshold: float) -> str:
    """Цвет бара по положению density относительно порога."""
    if density >= threshold * 1.3:
        return "#15803D"
    if density >= threshold:
        return "#B45309"
    return "#B91C1C"


def render(
    districts_df: pd.DataFrame,
    mo_df: pd.DataFrame,
    threshold: float,
    show_mo_markers: bool = False,
) -> None:
    """
    Рендерит страницу мониторинга.

    Args:
        districts_df: DataFrame с метриками по округам.
        mo_df: DataFrame со списком МО.
        threshold: Пороговое значение плотности из sidebar.
        show_mo_markers: Показывать ли маркеры МО на карте.
    """
    logger.info(
        "Рендеринг страницы мониторинга: %d округов, порог=%.1f",
        len(districts_df), threshold,
    )

    # ── KPI-карточки ─────────────────────────────────────────────────────────
    total_mo    = int(districts_df["total_mo"].sum())
    avg_density = round(float(districts_df["density"].mean()), 2)
    high_access = int((districts_df["accessibility_score"] > 0.7).sum())
    white_spots = int((districts_df["density"] < threshold).sum())

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown(
            f"""<div class="kpi-card kpi-blue">
              <div class="kpi-label">Всего МО в городе</div>
              <div class="kpi-value" style="color:#1D4ED8;">{total_mo:,}</div>
              <div class="kpi-sub">в {len(districts_df)} округах</div>
            </div>""",
            unsafe_allow_html=True,
        )
    with col2:
        st.markdown(
            f"""<div class="kpi-card kpi-green">
              <div class="kpi-label">Средняя плотность</div>
              <div class="kpi-value" style="color:#15803D;">{avg_density}</div>
              <div class="kpi-sub">МО / 10 000 жит.</div>
            </div>""",
            unsafe_allow_html=True,
        )
    with col3:
        st.markdown(
            f"""<div class="kpi-card kpi-orange">
              <div class="kpi-label">Высокая доступность</div>
              <div class="kpi-value" style="color:#B45309;">{high_access}</div>
              <div class="kpi-sub">округов (score &gt; 0,70)</div>
            </div>""",
            unsafe_allow_html=True,
        )
    with col4:
        st.markdown(
            f"""<div class="kpi-card kpi-red">
              <div class="kpi-label">Белых пятен</div>
              <div class="kpi-value" style="color:#B91C1C;">{white_spots}</div>
              <div class="kpi-sub">density &lt; {threshold:.1f}</div>
            </div>""",
            unsafe_allow_html=True,
        )

    st.markdown("<div style='margin-top:18px;'></div>", unsafe_allow_html=True)

    # ── Карта + таблица ───────────────────────────────────────────────────────
    map_col, table_col = st.columns([2, 1])

    with map_col:
        st.markdown(
            '<div class="section-title">Choropleth-карта плотности МО</div>',
            unsafe_allow_html=True,
        )
        show_markers = st.checkbox(
            "Показать маркеры МО", value=show_mo_markers, key="mon_markers"
        )
        try:
            folium_map = build_choropleth_map(districts_df, threshold=threshold)
            if show_markers:
                folium_map = add_mo_markers(folium_map, mo_df, cluster=True)
            st_folium(
                folium_map, height=420,
                use_container_width=True, returned_objects=[],
            )
        except Exception as exc:
            logger.error("Ошибка построения карты: %s", exc)
            st.error(f"Ошибка карты: {exc}")

    with table_col:
        st.markdown(
            '<div class="section-title">Рейтинг округов</div>',
            unsafe_allow_html=True,
        )
        table_df = (
            districts_df[["name", "total_mo", "density", "accessibility_score"]]
            .copy()
            .sort_values("density", ascending=False)
        )
        table_df["Статус"] = table_df["density"].apply(
            lambda d: _status_label(d, threshold)
        )
        table_df.columns = ["Округ", "МО", "Плотность", "Доступность", "Статус"]
        table_df["Плотность"]   = table_df["Плотность"].map("{:.2f}".format)
        table_df["Доступность"] = table_df["Доступность"].map("{:.1%}".format)

        st.dataframe(
            table_df,
            use_container_width=True,
            height=400,
            hide_index=True,
        )

    st.markdown("<div style='margin-top:8px;'></div>", unsafe_allow_html=True)

    # ── Bar chart — плотность МО по округам (переработанный) ─────────────────
    st.markdown(
        '<div class="section-title">Плотность МО по административным округам</div>',
        unsafe_allow_html=True,
    )

    chart_df = districts_df.sort_values("density").copy()
    chart_df["color"]   = chart_df["density"].apply(lambda d: _bar_color(d, threshold))
    chart_df["label"]   = chart_df["density"].map("{:.2f}".format)

    # Средняя плотность для справочной линии
    avg = float(districts_df["density"].mean())

    fig = go.Figure()

    # Основные бары
    fig.add_trace(
        go.Bar(
            x=chart_df["density"],
            y=chart_df["name"],
            orientation="h",
            marker=dict(
                color=chart_df["color"],
                line=dict(color="rgba(0,0,0,0.08)", width=0.5),
            ),
            text=chart_df["label"],
            textposition="outside",
            textfont=dict(size=11, color="#1E293B", family="Arial"),
            cliponaxis=False,
            hovertemplate=(
                "<b>%{y}</b><br>"
                "Плотность: <b>%{x:.2f}</b> МО / 10 000 жит.<extra></extra>"
            ),
            width=0.65,
        )
    )

    # Линия порога
    fig.add_vline(
        x=threshold,
        line_dash="dash",
        line_color="#2563EB",
        line_width=1.5,
        annotation_text=f"Порог {threshold:.1f}",
        annotation_position="top",
        annotation_font=dict(size=10, color="#2563EB"),
        annotation_bgcolor="white",
    )

    # Линия среднего
    fig.add_vline(
        x=avg,
        line_dash="dot",
        line_color="#64748B",
        line_width=1,
        annotation_text=f"Среднее {avg:.2f}",
        annotation_position="bottom",
        annotation_font=dict(size=10, color="#64748B"),
        annotation_bgcolor="white",
    )

    fig.update_layout(
        xaxis_title="МО / 10 000 жителей",
        yaxis_title=None,
        height=480,
        margin=dict(l=0, r=70, t=16, b=48),
        plot_bgcolor="white",
        paper_bgcolor="white",
        xaxis=dict(
            gridcolor="#F1F5F9",
            gridwidth=1,
            showline=True,
            linecolor="#E2E8F0",
            tickfont=dict(size=11, color="#475569"),
            title_font=dict(size=12, color="#475569"),
            zeroline=False,
        ),
        yaxis=dict(
            tickfont=dict(size=12, color="#1E293B"),
            showgrid=False,
        ),
        font=dict(family="Arial, sans-serif"),
        bargap=0.3,
    )

    # Легенда статусов (вручную через аннотации — чище)
    fig.add_annotation(
        xref="paper", yref="paper",
        x=1.0, y=-0.09, xanchor="right",
        text=(
            '<span style="color:#15803D">■</span> Норма   '
            '<span style="color:#B45309">■</span> Внимание   '
            '<span style="color:#B91C1C">■</span> Дефицит'
        ),
        showarrow=False,
        font=dict(size=11, color="#475569"),
    )

    st.plotly_chart(fig, use_container_width=True)
