"""
SQL-запросы к базе данных PostgreSQL/PostGIS.

Все функции возвращают pandas DataFrame. При отсутствии подключения к БД
автоматически используются mock-данные из data/mock_data.py.
Запросы используют PostGIS-функции для пространственного анализа.
"""

import logging
from typing import Optional

import pandas as pd

from db.connection import DatabaseConnection
from data.mock_data import (
    get_districts_dataframe,
    get_medical_objects_dataframe,
    get_metrics_history,
)

logger = logging.getLogger(__name__)


# ── Вспомогательная функция переключения источника данных ───────────────────

def _use_mock(func_name: str) -> None:
    """Логирует переключение на mock-данные."""
    logger.info("[%s] БД недоступна → используются mock-данные", func_name)


# ── Запросы к округам ────────────────────────────────────────────────────────

def get_all_districts(db: Optional[DatabaseConnection] = None) -> pd.DataFrame:
    """
    Возвращает все административные округа с рассчитанными метриками.

    PostGIS-запрос использует ST_AsGeoJSON для получения геометрии округов
    и COUNT + GROUP BY для агрегации медицинских объектов.

    Args:
        db: Активное соединение с БД. Если None или не подключено — mock.

    Returns:
        DataFrame с колонками: id, name, population, total_mo, density,
        accessibility_score, white_spots_count, geometry (GeoJSON).
    """
    SQL = """
        SELECT
            d.id,
            d.name,
            d.full_name,
            d.area_km2,
            d.population,
            d.lat,
            d.lon,
            COUNT(mo.id)                                                AS total_mo,
            COUNT(mo.id)::float / NULLIF(d.population / 10000.0, 0)    AS density,
            SUM(CASE WHEN mo.type = 'hospital'    THEN 1 ELSE 0 END)   AS hospitals,
            SUM(CASE WHEN mo.type = 'polyclinic'  THEN 1 ELSE 0 END)   AS polyclinics,
            SUM(CASE WHEN mo.type = 'ambulatory'  THEN 1 ELSE 0 END)   AS ambulatory,
            SUM(CASE WHEN mo.type = 'specialized' THEN 1 ELSE 0 END)   AS specialized,
            ST_AsGeoJSON(d.geom)::json                                  AS geometry
        FROM districts d
        LEFT JOIN medical_objects mo
               ON ST_Within(mo.location, d.geom)
        GROUP BY d.id, d.name, d.full_name, d.area_km2, d.population, d.lat, d.lon, d.geom
        ORDER BY density DESC NULLS LAST
    """
    if db is not None and db.is_connected:
        logger.debug("get_all_districts: запрос к БД")
        return db.get_dataframe(SQL)

    _use_mock("get_all_districts")
    return get_districts_dataframe()


def get_mo_by_district(
    district_name: str,
    db: Optional[DatabaseConnection] = None,
) -> pd.DataFrame:
    """
    Возвращает все МО в указанном административном округе.

    Использует PostGIS ST_Within для точной пространственной выборки.

    Args:
        district_name: Название округа (аббревиатура, например 'ЦАО').
        db: Активное соединение с БД.

    Returns:
        DataFrame с колонками: id, name, type, address, lat, lon, source,
        confidence_score.
    """
    SQL = """
        SELECT
            mo.id,
            mo.name,
            mo.type,
            mo.address,
            ST_Y(mo.location::geometry)  AS lat,
            ST_X(mo.location::geometry)  AS lon,
            mo.source,
            mo.confidence_score
        FROM medical_objects mo
        JOIN districts d ON ST_Within(mo.location, d.geom)
        WHERE d.name = %(district_name)s
        ORDER BY mo.type, mo.name
    """
    if db is not None and db.is_connected:
        logger.debug("get_mo_by_district: district=%s", district_name)
        return db.get_dataframe(SQL, {"district_name": district_name})

    _use_mock("get_mo_by_district")
    df = get_medical_objects_dataframe()
    return df[df["district"] == district_name].reset_index(drop=True)


def get_mo_by_type(
    mo_type: str,
    db: Optional[DatabaseConnection] = None,
) -> pd.DataFrame:
    """
    Возвращает все МО указанного типа с агрегацией по округам.

    Если mo_type == 'all' — возвращает все МО.

    PostGIS-запрос:
        SELECT d.name, COUNT(mo.id)::float / (d.population / 10000.0) as density,
               ST_AsGeoJSON(d.geom) as geometry
        FROM districts d
        LEFT JOIN medical_objects mo ON ST_Within(mo.location, d.geom)
        WHERE mo.type = %(mo_type)s OR %(mo_type)s = 'all'
        GROUP BY d.id, d.name, d.population, d.geom
        ORDER BY density DESC

    Args:
        mo_type: Тип МО ('hospital', 'polyclinic', 'ambulatory', 'specialized', 'all').
        db: Активное соединение с БД.

    Returns:
        DataFrame с МО.
    """
    SQL = """
        SELECT
            mo.id,
            mo.name,
            mo.type,
            d.name   AS district,
            mo.address,
            ST_Y(mo.location::geometry) AS lat,
            ST_X(mo.location::geometry) AS lon,
            mo.source,
            mo.confidence_score
        FROM medical_objects mo
        JOIN districts d ON ST_Within(mo.location, d.geom)
        WHERE mo.type = %(mo_type)s OR %(mo_type)s = 'all'
        ORDER BY d.name, mo.type, mo.name
    """
    if db is not None and db.is_connected:
        logger.debug("get_mo_by_type: type=%s", mo_type)
        return db.get_dataframe(SQL, {"mo_type": mo_type})

    _use_mock("get_mo_by_type")
    df = get_medical_objects_dataframe()
    if mo_type != "all":
        df = df[df["type"] == mo_type].reset_index(drop=True)
    return df


def get_metrics_history_db(
    district_name: str,
    months: int = 6,
    db: Optional[DatabaseConnection] = None,
) -> pd.DataFrame:
    """
    Возвращает историю метрик округа за последние N месяцев.

    Args:
        district_name: Название округа.
        months: Глубина истории в месяцах.
        db: Активное соединение с БД.

    Returns:
        DataFrame с колонками: month, density, accessibility_score, total_mo.
    """
    SQL = """
        SELECT
            TO_CHAR(mr.calculated_at, 'YYYY-MM') AS month,
            mr.density,
            mr.accessibility_score,
            mr.total_mo
        FROM metrics_results mr
        JOIN districts d ON mr.district_id = d.id
        WHERE d.name = %(district_name)s
          AND mr.calculated_at >= NOW() - INTERVAL '%(months)s months'
        ORDER BY mr.calculated_at
    """
    if db is not None and db.is_connected:
        logger.debug("get_metrics_history_db: district=%s, months=%d", district_name, months)
        return db.get_dataframe(SQL, {"district_name": district_name, "months": months})

    _use_mock("get_metrics_history_db")
    return get_metrics_history(district_name, months)


def get_white_spots(
    threshold: float,
    db: Optional[DatabaseConnection] = None,
) -> pd.DataFrame:
    """
    Возвращает округа, где плотность МО ниже заданного порога.

    Использует PostGIS ST_Distance для дополнительного расчёта
    минимального расстояния до ближайшей МО.

    Args:
        threshold: Пороговое значение density (МО / 10 000 жителей).
        db: Активное соединение с БД.

    Returns:
        DataFrame с колонками: name, density, deficit_mo, population.
    """
    SQL = """
        SELECT
            d.name,
            d.population,
            COUNT(mo.id)::float / NULLIF(d.population / 10000.0, 0) AS density,
            GREATEST(0,
                CEIL(%(threshold)s * d.population / 10000.0) - COUNT(mo.id)
            )::int AS deficit_mo,
            MIN(
                ST_Distance(
                    d.geom::geography,
                    mo.location::geography
                ) / 1000.0
            ) AS min_distance_km
        FROM districts d
        LEFT JOIN medical_objects mo ON ST_Within(mo.location, d.geom)
        GROUP BY d.id, d.name, d.population, d.geom
        HAVING COUNT(mo.id)::float / NULLIF(d.population / 10000.0, 0) < %(threshold)s
            OR COUNT(mo.id) = 0
        ORDER BY density ASC NULLS FIRST
    """
    if db is not None and db.is_connected:
        logger.debug("get_white_spots: threshold=%.1f", threshold)
        return db.get_dataframe(SQL, {"threshold": threshold})

    _use_mock("get_white_spots")
    df = get_districts_dataframe()
    ws = df[df["density"] < threshold][
        ["name", "full_name", "population", "density", "total_mo"]
    ].copy()
    ws["deficit_mo"] = (
        (threshold * ws["population"] / 10_000) - ws["total_mo"]
    ).clip(lower=0).astype(int)
    return ws.sort_values("density").reset_index(drop=True)


def insert_mo(mo_data: dict, db: Optional[DatabaseConnection] = None) -> bool:
    """
    Добавляет новый медицинский объект в базу данных.

    Использует PostGIS ST_SetSRID / ST_MakePoint для создания геометрии.

    Args:
        mo_data: Словарь с полями: name, type, district_id, address, lat, lon,
                 source, confidence_score.
        db: Активное соединение с БД.

    Returns:
        True если вставка успешна, False в противном случае.
    """
    SQL = """
        INSERT INTO medical_objects (name, type, district_id, address, location, source, confidence_score)
        VALUES (
            %(name)s,
            %(type)s,
            %(district_id)s,
            %(address)s,
            ST_SetSRID(ST_MakePoint(%(lon)s, %(lat)s), 4326)::geography,
            %(source)s,
            %(confidence_score)s
        )
        RETURNING id
    """
    if db is not None and db.is_connected:
        rows = db.execute_query(SQL, mo_data)
        success = len(rows) > 0
        logger.info("insert_mo: %s (id=%s)", mo_data.get("name"), rows[0]["id"] if success else "—")
        return success

    logger.info("insert_mo: mock-режим, данные не сохранены: %s", mo_data.get("name"))
    return False


def update_metrics(
    district_id: int,
    metrics: dict,
    db: Optional[DatabaseConnection] = None,
) -> bool:
    """
    Обновляет метрики округа в таблице metrics_results.

    Args:
        district_id: ID округа.
        metrics: Словарь с полями: density, accessibility_score, total_mo.
        db: Активное соединение с БД.

    Returns:
        True если обновление успешно.
    """
    SQL = """
        INSERT INTO metrics_results (district_id, density, accessibility_score, total_mo, calculated_at)
        VALUES (%(district_id)s, %(density)s, %(accessibility_score)s, %(total_mo)s, NOW())
        ON CONFLICT (district_id, DATE(calculated_at))
        DO UPDATE SET
            density             = EXCLUDED.density,
            accessibility_score = EXCLUDED.accessibility_score,
            total_mo            = EXCLUDED.total_mo,
            calculated_at       = NOW()
    """
    params = {"district_id": district_id, **metrics}
    if db is not None and db.is_connected:
        rows = db.execute_query(SQL, params)
        logger.info("update_metrics: district_id=%d обновлён", district_id)
        return True

    logger.info("update_metrics: mock-режим, district_id=%d не сохранён", district_id)
    return False
