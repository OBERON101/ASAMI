"""
ETL-модуль загрузки данных о медицинских организациях.

Имитирует получение данных из двух источников:
1. Официальный реестр МО Министерства здравоохранения
2. OpenStreetMap через Overpass API

В реальной системе методы выполняли бы HTTP-запросы к указанным URL.
"""

import logging
import random
from datetime import datetime
from typing import Optional

import pandas as pd

logger = logging.getLogger(__name__)

# Реальный URL Overpass API (в демо не используется):
# OVERPASS_URL = "https://overpass-api.de/api/interpreter"
# OVERPASS_QUERY = """
# [out:json][timeout:60];
# area["name"="Москва"]["admin_level"="4"]->.moscow;
# (
#   node["amenity"~"hospital|clinic|doctors"](area.moscow);
#   way["amenity"~"hospital|clinic|doctors"](area.moscow);
# );
# out center tags;
# """

# Официальный реестр МО (заглушка):
# OFFICIAL_API_URL = "https://nsi.rosminzdrav.ru/#!/refbook/1.2.643.5.1.13.13.11.1461"


class DataLoader:
    """
    Загрузчик данных о медицинских организациях из внешних источников.

    Поддерживает официальный реестр Минздрава и OpenStreetMap.
    В демонстрационном режиме возвращает сгенерированные данные.
    """

    def __init__(self) -> None:
        """Инициализация загрузчика."""
        self._snapshots: dict[str, pd.DataFrame] = {}
        logger.info("DataLoader инициализирован")

    def load_from_official_source(self, city: str = "Moscow") -> pd.DataFrame:
        """
        Имитирует загрузку данных из официального реестра МО.

        В реальной системе выполнял бы GET-запрос к API Минздрава
        с последующим парсингом JSON/XML-ответа.

        Args:
            city: Название города для фильтрации (по умолчанию 'Moscow').

        Returns:
            DataFrame с 12 записями МО из официального источника.
        """
        logger.info("load_from_official_source: загрузка для города '%s'", city)

        records = [
            {"name": "ГКБ №1 им. Пирогова",         "type_raw": "Больница",             "address": "Ленинский пр-т, 8",          "district": "ЦАО"},
            {"name": "Поликлиника №5",               "type_raw": "Поликлиника",           "address": "ул. Арбат, 28",              "district": "ЦАО"},
            {"name": "НМИЦ онкологии",               "type_raw": "Специализированный центр","address": "Каширское ш., 23",          "district": "ЦАО"},
            {"name": "ГКБ №50",                      "type_raw": "Больница",             "address": "Вучетича ул., 21",           "district": "САО"},
            {"name": "Поликлиника №114",             "type_raw": "Поликлиника",           "address": "Бол. Академическая ул., 6", "district": "САО"},
            {"name": "ГКБ №40",                      "type_raw": "Больница",             "address": "Сосенское пос., 5",          "district": "СВАО"},
            {"name": "Поликлиника №32",              "type_raw": "Поликлиника",           "address": "Ростокинская ул., 5",        "district": "СВАО"},
            {"name": "ГКБ №36",                      "type_raw": "Больница",             "address": "Фортунатовская ул., 1",      "district": "ВАО"},
            {"name": "Поликлиника №71",              "type_raw": "Поликлиника",           "address": "Люблинская ул., 37",         "district": "ЮВАО"},
            {"name": "ГКБ №13",                      "type_raw": "Больница",             "address": "Велозаводская ул., 1",       "district": "ЮВАО"},
            {"name": "Поликлиника №116",             "type_raw": "Поликлиника",           "address": "Болотниковская ул., 5",      "district": "ЮАО"},
            {"name": "ГКБ №67",                      "type_raw": "Больница",             "address": "Саляма Адиля ул., 2",        "district": "ЗАО"},
        ]

        df = pd.DataFrame(records)
        df["source"] = "официальный"
        df["confidence_score"] = [round(random.uniform(0.88, 0.99), 2) for _ in range(len(df))]
        df["loaded_at"] = datetime.now().isoformat()

        self._snapshots["official"] = df
        logger.info("Загружено %d записей из официального источника", len(df))
        return df

    def load_from_osm(self, city: str = "Moscow") -> pd.DataFrame:
        """
        Имитирует загрузку данных из OpenStreetMap через Overpass API.

        В реальной системе выполнял бы POST-запрос к Overpass API:
            POST https://overpass-api.de/api/interpreter
            data=[out:json]; area["name"="Москва"]->.m; node["amenity"="hospital"](area.m); out;

        Args:
            city: Название города для формирования Overpass-запроса.

        Returns:
            DataFrame с 10 записями МО из OSM.
        """
        logger.info("load_from_osm: имитация запроса к Overpass API для '%s'", city)

        records = [
            {"name": "Клиника Медицина",             "type_raw": "Клиника",         "address": "2-й Тверской-Ямской пер., 10", "district": "ЦАО",  "osm_id": 123456},
            {"name": "Амбулатория Пресненского р-на","type_raw": "Амбулатория",      "address": "Мал. Конюшковская ул., 8",     "district": "ЦАО",  "osm_id": 123457},
            {"name": "Амбулатория Ховрино",          "type_raw": "Амбулатория",      "address": "Фестивальная ул., 35",         "district": "САО",  "osm_id": 234501},
            {"name": "Поликлиника №211",             "type_raw": "Поликлиника",      "address": "Клязьминская ул., 12",         "district": "САО",  "osm_id": 234502},
            {"name": "Лосиноостровская пол-ка №96",  "type_raw": "Поликлиника",      "address": "Ярославское ш., 116",          "district": "СВАО", "osm_id": 345601},
            {"name": "Амбулатория Бабушкинская",     "type_raw": "Амбулатория",      "address": "Ярославское ш., 48А",          "district": "СВАО", "osm_id": 345602},
            {"name": "МФЦ здоровья Измайлово",       "type_raw": "Диагностический центр","address": "Измайловский пр-т, 43",   "district": "ВАО",  "osm_id": 456701},
            {"name": "Амбулатория Богородское",      "type_raw": "Амбулатория",      "address": "Краснобогатырская ул., 2",     "district": "ВАО",  "osm_id": 456702},
            {"name": "Амбулатория Текстильщики",     "type_raw": "Амбулатория",      "address": "Волгоградский пр-т, 104",      "district": "ЮВАО", "osm_id": 567801},
            {"name": "Амбулатория Бирюлёво Западное","type_raw": "Амбулатория",      "address": "Загорьевская ул., 6А",         "district": "ЮАО",  "osm_id": 678901},
        ]

        df = pd.DataFrame(records)
        df["source"] = "OSM"
        df["confidence_score"] = [round(random.uniform(0.72, 0.89), 2) for _ in range(len(df))]
        df["loaded_at"] = datetime.now().isoformat()

        self._snapshots["osm"] = df
        logger.info("Загружено %d записей из OSM", len(df))
        return df

    def save_raw_snapshot(self, data: pd.DataFrame, source_name: str) -> str:
        """
        Сохраняет снапшот сырых данных с меткой времени.

        В реальной системе сохранял бы в файл или S3-совместимое хранилище.

        Args:
            data: DataFrame для сохранения.
            source_name: Идентификатор источника ('official', 'osm').

        Returns:
            Имя файла снапшота (mock).
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"snapshot_{source_name}_{timestamp}.csv"

        self._snapshots[source_name] = data
        logger.info(
            "Снапшот '%s' сохранён: %d строк (mock, файл не создаётся: %s)",
            source_name, len(data), filename
        )
        return filename

    def get_combined(self) -> pd.DataFrame:
        """
        Объединяет данные из всех загруженных источников.

        Returns:
            Объединённый DataFrame или пустой, если данные не загружались.
        """
        if not self._snapshots:
            logger.warning("get_combined: нет загруженных снапшотов")
            return pd.DataFrame()

        combined = pd.concat(list(self._snapshots.values()), ignore_index=True)
        logger.info("Объединено %d записей из %d источников", len(combined), len(self._snapshots))
        return combined
