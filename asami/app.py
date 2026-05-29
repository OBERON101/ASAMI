"""
АСАМИ — Автоматизированная система анализа медицинской инфраструктуры.

Главный модуль запуска Streamlit-приложения.
Запуск: streamlit run app.py

Архитектура:
    app.py → pages/Мониторинг.py   — вкладка «Мониторинг»
           → pages/Фильтрация.py   — вкладка «Фильтрация»
           → pages/Белые_пятна.py  — вкладка «Белые пятна»

Данные:
    - При доступности PostgreSQL/PostGIS: db/queries.py → реальные данные
    - При отсутствии БД: data/mock_data.py → демонстрационные данные
"""

import logging
import sys

import pandas as pd
import streamlit as st

# ── Конфигурация страницы (должна быть первым вызовом Streamlit) ─────────────
st.set_page_config(
    page_title="АСАМИ — Медицинская инфраструктура",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        "About": "АСАМИ v1.0 — Дипломный прототип анализа медицинской инфраструктуры",
    },
)

# ── Логирование ───────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)

# ── Импорты модулей проекта ───────────────────────────────────────────────────
try:
    from config import (
        APP_TITLE, APP_SUBTITLE, APP_VERSION,
        CITIES, DEFAULT_DENSITY_THRESHOLD,
        DENSITY_THRESHOLD_MIN, DENSITY_THRESHOLD_MAX, DENSITY_THRESHOLD_STEP,
        COLORS,
    )
    from db.connection import check_db_status
    from data.mock_data import get_districts_dataframe, get_medical_objects_dataframe
    from metrics.calculator import MetricsEngine
    import pages.Мониторинг  as page_monitoring
    import pages.Фильтрация  as page_filter
    import pages.Белые_пятна as page_white_spots
except ImportError as exc:
    st.error(f"Ошибка импорта модуля: {exc}")
    st.stop()

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown(
    """
    <style>
    /* ── Общий шрифт ── */
    html, body, [data-testid="stAppViewContainer"] {
        font-family: 'Segoe UI', Arial, sans-serif;
    }

    /* ── Шапка приложения ── */
    .app-header {
        background: #1B3A6B;
        color: white;
        padding: 14px 24px 12px;
        border-bottom: 3px solid #2563EB;
        margin-bottom: 18px;
    }
    .app-header h1 {
        font-size: 20px;
        font-weight: 700;
        margin: 0;
        letter-spacing: 0.2px;
    }
    .app-header p {
        font-size: 12px;
        opacity: 0.75;
        margin: 3px 0 0;
        font-weight: 400;
    }

    /* ── KPI-карточки ── */
    .kpi-card {
        padding: 14px 18px;
        border-radius: 4px;
        border-left: 3px solid;
        margin-bottom: 4px;
    }
    .kpi-blue   { border-color: #2563EB; background: #F0F5FF; }
    .kpi-green  { border-color: #15803D; background: #F0FDF4; }
    .kpi-orange { border-color: #B45309; background: #FFFBEB; }
    .kpi-red    { border-color: #B91C1C; background: #FEF2F2; }

    .kpi-label {
        font-size: 10px;
        color: #475569;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.8px;
    }
    .kpi-value {
        font-size: 28px;
        font-weight: 700;
        line-height: 1.15;
        margin: 4px 0 2px;
    }
    .kpi-sub {
        font-size: 11px;
        color: #64748B;
    }

    /* ── Статус БД ── */
    .db-status {
        padding: 6px 10px;
        border-radius: 3px;
        font-size: 11px;
        font-weight: 600;
        margin-bottom: 6px;
    }
    .db-ok   { background: #F0FDF4; color: #15803D; border: 1px solid #BBF7D0; }
    .db-fail { background: #FEF2F2; color: #991B1B; border: 1px solid #FECACA; }

    /* ── Вкладки — строже ── */
    [data-baseweb="tab-list"] { gap: 0; border-bottom: 2px solid #E2E8F0; }
    [data-baseweb="tab"] {
        font-weight: 600;
        font-size: 13px;
        padding: 10px 20px;
        border-radius: 0;
    }

    /* ── Подраздел страницы ── */
    .section-title {
        font-size: 13px;
        font-weight: 700;
        color: #1B3A6B;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        border-bottom: 2px solid #E2E8F0;
        padding-bottom: 6px;
        margin-bottom: 12px;
    }

    /* ── Скрыть подвал и оригинальную кнопку деплоя Streamlit (английский диалог) ── */
    footer { visibility: hidden; }
    [data-testid="stDeployButton"] { display: none !important; }

    /* ── Кнопка развёртывания (кастомная) ── */
    .deploy-btn {
        display: block;
        width: 100%;
        padding: 8px 12px;
        background: #1B3A6B;
        color: white !important;
        border: none;
        border-radius: 4px;
        font-size: 12px;
        font-weight: 600;
        text-align: center;
        cursor: pointer;
        text-decoration: none;
        margin-top: 6px;
        letter-spacing: 0.3px;
    }
    .deploy-btn:hover { background: #2563EB; }
    </style>
    """,
    unsafe_allow_html=True,
)


# ── Кеширование данных ────────────────────────────────────────────────────────

@st.cache_data(ttl=300, show_spinner=False)
def load_districts() -> pd.DataFrame:
    """
    Загружает данные по округам с кешированием на 5 минут.

    При доступности БД — из PostgreSQL, иначе — из mock_data.

    Returns:
        DataFrame с метриками по 12 округам Москвы.
    """
    try:
        engine = MetricsEngine()
        df = get_districts_dataframe()
        df = engine.calculate_all(df)
        logger.info("Данные по округам загружены: %d строк", len(df))
        return df
    except Exception as exc:
        logger.error("Ошибка загрузки данных по округам: %s", exc)
        return pd.DataFrame()


@st.cache_data(ttl=300, show_spinner=False)
def load_medical_objects() -> pd.DataFrame:
    """
    Загружает список медицинских организаций с кешированием.

    Returns:
        DataFrame с 50 МО.
    """
    try:
        df = get_medical_objects_dataframe()
        logger.info("МО загружены: %d записей", len(df))
        return df
    except Exception as exc:
        logger.error("Ошибка загрузки МО: %s", exc)
        return pd.DataFrame()


@st.cache_data(ttl=60, show_spinner=False)
def get_db_status_cached() -> tuple[bool, str]:
    """
    Проверяет статус БД с кешированием на 1 минуту.

    Returns:
        Кортеж (is_connected, message).
    """
    try:
        return check_db_status()
    except Exception as exc:
        return False, str(exc)


# ── Sidebar ───────────────────────────────────────────────────────────────────

def render_sidebar() -> tuple[float, list[str], bool]:
    """
    Рендерит боковую панель с параметрами анализа.

    Returns:
        Кортеж (threshold, selected_types, refresh_clicked).
    """
    with st.sidebar:
        # Логотип и заголовок панели
        st.markdown(
            """
            <div style="padding:14px 0 10px;">
              <div style="font-size:13px;font-weight:700;color:#1B3A6B;
                          letter-spacing:1px;text-transform:uppercase;">
                АСАМИ
              </div>
              <div style="font-size:10px;color:#94A3B8;margin-top:2px;">
                Анализ медицинской инфраструктуры
              </div>
            </div>
            <hr style="border:none;border-top:1px solid #E2E8F0;margin:0 0 10px;">
            """,
            unsafe_allow_html=True,
        )

        # ── Статус подключения к БД ──────────────────────────────────────────
        with st.spinner("Проверка БД..."):
            db_ok, db_msg = get_db_status_cached()

        if db_ok:
            st.markdown(
                '<div class="db-status db-ok">БД подключена</div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                '<div class="db-status db-fail">БД недоступна — демо-режим</div>',
                unsafe_allow_html=True,
            )

        st.markdown(
            '<div style="font-size:10px;color:#94A3B8;margin-bottom:14px;">'
            'PostgreSQL/PostGIS · localhost:5432</div>',
            unsafe_allow_html=True,
        )

        # ── Выбор города ────────────────────────────────────────────────────
        st.selectbox("Город", options=CITIES, key="selected_city")

        st.divider()

        # ── Порог плотности МО ───────────────────────────────────────────────
        st.markdown(
            '<div style="font-size:11px;font-weight:700;color:#334155;'
            'text-transform:uppercase;letter-spacing:0.5px;margin-bottom:6px;">'
            'Порог плотности МО</div>',
            unsafe_allow_html=True,
        )
        threshold = st.slider(
            "МО / 10 000 жителей",
            min_value=DENSITY_THRESHOLD_MIN,
            max_value=DENSITY_THRESHOLD_MAX,
            value=DEFAULT_DENSITY_THRESHOLD,
            step=DENSITY_THRESHOLD_STEP,
            key="density_threshold",
            label_visibility="collapsed",
        )
        st.markdown(
            f'<div style="text-align:center;font-size:20px;font-weight:700;'
            f'color:#1B3A6B;margin:-6px 0 6px;">{threshold:.1f}'
            f'<span style="font-size:11px;font-weight:400;color:#64748B;'
            f'margin-left:4px;">МО / 10 000</span></div>',
            unsafe_allow_html=True,
        )

        st.divider()

        # ── Фильтры по типам МО ──────────────────────────────────────────────
        st.markdown(
            '<div style="font-size:11px;font-weight:700;color:#334155;'
            'text-transform:uppercase;letter-spacing:0.5px;margin-bottom:8px;">'
            'Типы МО</div>',
            unsafe_allow_html=True,
        )
        show_hospitals   = st.checkbox("Больницы",          value=True, key="chk_hospital")
        show_polyclinics = st.checkbox("Поликлиники",       value=True, key="chk_polyclinic")
        show_ambulatory  = st.checkbox("Амбулатории",       value=True, key="chk_ambulatory")
        show_specialized = st.checkbox("Спец. центры",      value=True, key="chk_specialized")

        selected_types: list[str] = []
        if show_hospitals:   selected_types.append("hospital")
        if show_polyclinics: selected_types.append("polyclinic")
        if show_ambulatory:  selected_types.append("ambulatory")
        if show_specialized: selected_types.append("specialized")

        st.divider()

        # ── Кнопка обновления ───────────────────────────────────────────────
        refresh = st.button(
            "Обновить данные",
            use_container_width=True,
            key="btn_refresh",
            help="Перезагружает данные из источника данных",
        )

        if refresh:
            load_districts.clear()
            load_medical_objects.clear()
            get_db_status_cached.clear()
            st.rerun()

        st.divider()

        # ── Развёртывание ─────────────────────────────────────────────────────
        st.markdown(
            '<div style="font-size:11px;font-weight:700;color:#334155;'
            'text-transform:uppercase;letter-spacing:0.5px;margin-bottom:8px;">'
            'Развёртывание</div>',
            unsafe_allow_html=True,
        )

        with st.expander("Варианты развёртывания", expanded=False):
            st.markdown(
                """
                **Streamlit Community Cloud**
                - Бесплатно для публичных репозиториев
                - Развёртывание через GitHub за 1 клик
                - Автоматическое обновление при push

                **Собственный сервер**
                - Docker / Docker Compose
                - Kubernetes
                - Любой Linux-хост с Python 3.9+

                **Команды для запуска:**
                ```bash
                # Локально
                streamlit run app.py

                # Docker
                docker build -t asami .
                docker run -p 8501:8501 asami
                ```
                """,
            )
            st.link_button(
                "Документация по развёртыванию",
                url="https://docs.streamlit.io/deploy",
                use_container_width=True,
            )

        # ── Версия ───────────────────────────────────────────────────────────
        st.markdown(
            f'<div style="margin-top:14px;font-size:10px;color:#CBD5E1;'
            f'text-align:center;">АСАМИ {APP_VERSION} · 2025</div>',
            unsafe_allow_html=True,
        )

    return threshold, selected_types, refresh


# ── Главная функция ───────────────────────────────────────────────────────────

def main() -> None:
    """
    Точка входа в приложение АСАМИ.

    Инициализирует данные, отрисовывает sidebar и три вкладки интерфейса.
    """
    logger.info("Запуск приложения АСАМИ")

    # ── Шапка ────────────────────────────────────────────────────────────────
    st.markdown(
        f"""
        <div class="app-header">
          <h1>{APP_TITLE}</h1>
          <p>{APP_SUBTITLE}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── Sidebar ───────────────────────────────────────────────────────────────
    threshold, selected_types, _ = render_sidebar()

    # ── Загрузка данных ───────────────────────────────────────────────────────
    with st.spinner("Загрузка данных..."):
        districts_df = load_districts()
        mo_df        = load_medical_objects()

    if districts_df.empty:
        st.error(
            "Не удалось загрузить данные по округам. "
            "Проверьте наличие файла data/mock_data.py."
        )
        st.stop()

    # Уведомление о режиме работы (только если БД недоступна)
    db_ok, _ = get_db_status_cached()
    if not db_ok:
        st.info(
            "Подключение к базе данных PostgreSQL/PostGIS не установлено. "
            "Система работает с демонстрационными данными. "
            "Настройте параметры в config.py для подключения к реальной БД."
        )

    # Фильтрация МО по выбранным типам
    if selected_types and not mo_df.empty:
        mo_filtered = mo_df[mo_df["type"].isin(selected_types)].copy()
    else:
        mo_filtered = mo_df.copy()

    # ── Вкладки ───────────────────────────────────────────────────────────────
    tab1, tab2, tab3 = st.tabs([
        "Мониторинг",
        "Фильтрация",
        "Белые пятна",
    ])

    with tab1:
        try:
            page_monitoring.render(
                districts_df=districts_df,
                mo_df=mo_filtered,
                threshold=threshold,
            )
        except Exception as exc:
            logger.error("Ошибка на вкладке Мониторинг: %s", exc, exc_info=True)
            st.error(f"Ошибка вкладки «Мониторинг»: {exc}")

    with tab2:
        try:
            page_filter.render(
                districts_df=districts_df,
                mo_df=mo_df,
                threshold=threshold,
            )
        except Exception as exc:
            logger.error("Ошибка на вкладке Фильтрация: %s", exc, exc_info=True)
            st.error(f"Ошибка вкладки «Фильтрация»: {exc}")

    with tab3:
        try:
            page_white_spots.render(
                districts_df=districts_df,
                threshold=threshold,
            )
        except Exception as exc:
            logger.error("Ошибка на вкладке Белые пятна: %s", exc, exc_info=True)
            st.error(f"Ошибка вкладки «Белые пятна»: {exc}")


# ── Точка входа ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    main()
