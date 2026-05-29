"""
ETL-модуль геокодирования адресов медицинских организаций.

Имитирует обращение к Nominatim API (OSM) для получения координат
по текстовому адресу. В реальной системе выполнял бы HTTP-запросы
к публичному или локальному инстансу Nominatim.
"""

import logging
import random
import time
from typing import Optional

import pandas as pd

logger = logging.getLogger(__name__)

# Реальный URL Nominatim API:
# NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
# Пример запроса:
#   GET https://nominatim.openstreetmap.org/search
#       ?q=Москва%2C+Ленинский+проспект+8&format=json&limit=1&countrycodes=ru
#   Заголовок User-Agent обязателен по политике Nominatim.

# Bounding box Москвы (WGS84)
MOSCOW_LAT_MIN, MOSCOW_LAT_MAX = 55.55, 55.90
MOSCOW_LON_MIN, MOSCOW_LON_MAX = 37.35, 37.85

# Центроиды округов для более реалистичного геокодирования
DISTRICT_CENTROIDS: dict[str, tuple[float, float]] = {
    "ЦАО":   (55.7558, 37.6173),
    "САО":   (55.8500, 37.5200),
    "СВАО":  (55.8700, 37.6800),
    "ВАО":   (55.7800, 37.8100),
    "ЮВАО":  (55.7000, 37.7700),
    "ЮАО":   (55.6400, 37.6200),
    "ЮЗАО":  (55.6600, 37.5200),
    "ЗАО":   (55.7400, 37.3900),
    "СЗАО":  (55.8200, 37.4000),
    "ЗеАО":  (55.9900, 37.1900),
    "НАО":   (55.5200, 37.2800),
    "ТиНАО": (55.3600, 37.2800),
}


class GeocoderModule:
    """
    Модуль геокодирования адресов через Nominatim OpenStreetMap API.

    В демонстрационном режиме возвращает случайные координаты в пределах
    Москвы с небольшим смещением от центроида округа.
    """

    def __init__(self, delay: float = 1.0) -> None:
        """
        Инициализация геокодера.

        Args:
            delay: Задержка между запросами в секундах (политика Nominatim:
                   не более 1 запроса в секунду).
        """
        self._delay = delay
        self._cache: dict[str, tuple[float, float]] = {}
        self._requests_count = 0
        logger.info("GeocoderModule инициализирован (задержка=%.1f с)", delay)

    def geocode(
        self,
        address: str,
        district: Optional[str] = None,
    ) -> tuple[float, float]:
        """
        Геокодирует текстовый адрес в координаты (lat, lon).

        В реальной системе выполнял бы:
            import requests
            resp = requests.get(
                "https://nominatim.openstreetmap.org/search",
                params={"q": f"Москва, {address}", "format": "json", "limit": 1},
                headers={"User-Agent": "ASAMI/1.0 student-diploma"},
                timeout=10,
            )
            data = resp.json()
            return float(data[0]["lat"]), float(data[0]["lon"])

        Args:
            address: Текстовый адрес для геокодирования.
            district: Название округа для смещения координат (улучшает реализм).

        Returns:
            Кортеж (lat, lon) — координаты в системе WGS84.
        """
        # Проверка кеша
        cache_key = f"{address}|{district}"
        if cache_key in self._cache:
            logger.debug("geocode: кеш-хит для '%s'", address)
            return self._cache[cache_key]

        self._requests_count += 1
        logger.debug("geocode: запрос #%d для адреса '%s'", self._requests_count, address)

        # Базовые координаты: центроид округа или центр Москвы
        if district and district in DISTRICT_CENTROIDS:
            base_lat, base_lon = DISTRICT_CENTROIDS[district]
        else:
            base_lat, base_lon = 55.7558, 37.6173

        # Случайное смещение ±0.03° (~3 км)
        lat = round(base_lat + random.uniform(-0.03, 0.03), 6)
        lon = round(base_lon + random.uniform(-0.04, 0.04), 6)

        # Clamp в пределах Москвы
        lat = max(MOSCOW_LAT_MIN, min(MOSCOW_LAT_MAX, lat))
        lon = max(MOSCOW_LON_MIN, min(MOSCOW_LON_MAX, lon))

        result = (lat, lon)
        self._cache[cache_key] = result
        logger.debug("geocode: '%s' → (%.4f, %.4f)", address, lat, lon)
        return result

    def batch_geocode(
        self,
        addresses: list[str],
        districts: Optional[list[str]] = None,
        delay: Optional[float] = None,
    ) -> list[tuple[float, float]]:
        """
        Пакетное геокодирование списка адресов.

        Соблюдает политику Nominatim: пауза между запросами.
        В реальной системе добавлял бы обработку ошибок 429 Too Many Requests.

        Args:
            addresses: Список текстовых адресов.
            districts: Список округов (параллельный addresses).
            delay: Задержка между запросами (переопределяет self._delay).

        Returns:
            Список кортежей (lat, lon) в том же порядке, что и addresses.
        """
        effective_delay = delay if delay is not None else self._delay
        results: list[tuple[float, float]] = []

        logger.info("batch_geocode: %d адресов, задержка=%.1f с", len(addresses), effective_delay)

        for i, address in enumerate(addresses):
            district = districts[i] if districts and i < len(districts) else None
            coords = self.geocode(address, district)
            results.append(coords)

            # Имитация задержки (в реальной системе time.sleep(effective_delay))
            # time.sleep(effective_delay)

        logger.info("batch_geocode: геокодировано %d адресов", len(results))
        return results

    def geocode_dataframe(
        self,
        df: pd.DataFrame,
        address_col: str = "address",
        district_col: Optional[str] = "district",
    ) -> pd.DataFrame:
        """
        Добавляет колонки lat/lon к DataFrame на основе адресной колонки.

        Args:
            df: DataFrame с адресами.
            address_col: Имя колонки с адресами.
            district_col: Имя колонки с округами (или None).

        Returns:
            DataFrame с добавленными колонками lat, lon.
        """
        result = df.copy()
        if address_col not in result.columns:
            logger.error("geocode_dataframe: колонка '%s' не найдена", address_col)
            result["lat"] = 55.7558
            result["lon"] = 37.6173
            return result

        addresses = result[address_col].tolist()
        districts = (
            result[district_col].tolist()
            if district_col and district_col in result.columns
            else None
        )

        coords = self.batch_geocode(addresses, districts)
        result["lat"] = [c[0] for c in coords]
        result["lon"] = [c[1] for c in coords]

        logger.info(
            "geocode_dataframe: добавлены координаты для %d строк", len(result)
        )
        return result

    def get_stats(self) -> dict:
        """
        Возвращает статистику работы геокодера.

        Returns:
            Словарь с количеством запросов и размером кеша.
        """
        return {
            "requests_total": self._requests_count,
            "cache_size": len(self._cache),
        }
