"""
ETL-модуль нормализации и классификации данных о МО.

Приводит разнородные данные из разных источников к единому стандарту:
- унификация названий полей
- стандартизация типов МО
- дедупликация записей
"""

import logging
import random
import re
from typing import Optional

import pandas as pd

logger = logging.getLogger(__name__)

# Попытка импорта rapidfuzz (для реальной дедупликации по схожести строк)
try:
    from rapidfuzz import fuzz
    RAPIDFUZZ_AVAILABLE = True
except ImportError:
    RAPIDFUZZ_AVAILABLE = False
    logger.warning("rapidfuzz не установлен, дедупликация работает в упрощённом режиме")

# Стандартный справочник типов МО
TYPE_REGISTRY = {
    "hospital":    "Больница",
    "polyclinic":  "Поликлиника",
    "ambulatory":  "Амбулатория",
    "specialized": "Специализированный центр",
}

# Паттерны для определения типа МО по названию
TYPE_PATTERNS: list[tuple[str, str]] = [
    (r"больниц|гкб|скб|цкб|нмиц",                  "hospital"),
    (r"поликлиник|дгп|взрослая поликлин",            "polyclinic"),
    (r"амбулатор",                                   "ambulatory"),
    (r"центр|диспансер|диагностич|стоматол|перинат", "specialized"),
    (r"клиник|медицин",                              "polyclinic"),
]

# Карта нормализации названий полей входных данных
FIELD_MAP = {
    "type_raw":     "type_raw",
    "наименование": "name",
    "адрес":        "address",
    "округ":        "district",
    "район":        "district",
    "тип":          "type_raw",
    "источник":     "source",
}


class NormalizationService:
    """
    Сервис нормализации и унификации данных о медицинских организациях.

    Обеспечивает совместимость данных из разных источников (официальный реестр,
    OSM, ручной ввод) для последующей загрузки в единую БД.
    """

    def __init__(self) -> None:
        """Инициализация сервиса."""
        self._stats: dict[str, int] = {}
        logger.info("NormalizationService инициализирован")

    def normalize(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Нормализует DataFrame: унифицирует поля и приводит типы МО к стандарту.

        Args:
            df: Исходный DataFrame из любого источника.

        Returns:
            Нормализованный DataFrame со стандартными колонками.
        """
        logger.info("normalize: начало обработки %d строк", len(df))
        result = df.copy()

        # Переименование колонок по карте
        rename_map = {
            old: new for old, new in FIELD_MAP.items() if old in result.columns
        }
        if rename_map:
            result.rename(columns=rename_map, inplace=True)
            logger.debug("Переименованы колонки: %s", rename_map)

        # Гарантируем наличие обязательных полей
        for col in ["name", "type_raw", "address", "district", "source", "confidence_score"]:
            if col not in result.columns:
                result[col] = None

        # Нормализация типа МО
        if "type_raw" in result.columns:
            result["type"] = result["type_raw"].apply(self.classify_type)
        elif "type" not in result.columns:
            result["type"] = "polyclinic"

        # Очистка строковых полей
        for col in ["name", "address", "district"]:
            if col in result.columns:
                result[col] = result[col].astype(str).str.strip()

        # Приведение confidence_score к float
        result["confidence_score"] = pd.to_numeric(
            result.get("confidence_score"), errors="coerce"
        ).fillna(0.8)

        self._stats["normalized"] = len(result)
        logger.info("normalize: завершено, %d строк после нормализации", len(result))
        return result

    def classify_type(self, raw_name: Optional[str]) -> str:
        """
        Определяет тип МО по сырому названию через регулярные выражения.

        Args:
            raw_name: Сырое название типа или наименование МО.

        Returns:
            Стандартный код типа: 'hospital', 'polyclinic', 'ambulatory', 'specialized'.
        """
        if not raw_name or not isinstance(raw_name, str):
            return "polyclinic"

        name_lower = raw_name.lower().strip()
        for pattern, mo_type in TYPE_PATTERNS:
            if re.search(pattern, name_lower, re.IGNORECASE):
                logger.debug("classify_type: '%s' → %s", raw_name, mo_type)
                return mo_type

        logger.debug("classify_type: '%s' → polyclinic (по умолчанию)", raw_name)
        return "polyclinic"

    def deduplicate(self, df: pd.DataFrame, threshold: float = 0.6) -> pd.DataFrame:
        """
        Удаляет дублирующиеся МО по схожести названий и адресов.

        В реальной системе использует rapidfuzz.fuzz.token_sort_ratio
        для попарного сравнения строк. В демо-режиме имитирует процесс
        через случайный отбор.

        Args:
            df: DataFrame с потенциальными дублями.
            threshold: Порог схожести [0, 1] для объединения записей.

        Returns:
            DataFrame без дублей.
        """
        logger.info(
            "deduplicate: %d записей, порог=%.2f, rapidfuzz=%s",
            len(df), threshold, RAPIDFUZZ_AVAILABLE
        )

        if RAPIDFUZZ_AVAILABLE and "name" in df.columns and len(df) > 1:
            # Реальное попарное сравнение (ресурсоёмко для больших датасетов)
            keep_mask = [True] * len(df)
            names = df["name"].tolist()
            for i in range(len(names)):
                if not keep_mask[i]:
                    continue
                for j in range(i + 1, len(names)):
                    if not keep_mask[j]:
                        continue
                    score = fuzz.token_sort_ratio(names[i], names[j]) / 100.0
                    if score >= threshold:
                        keep_mask[j] = False
                        logger.debug(
                            "Дубль: '%s' ≈ '%s' (score=%.2f)", names[i], names[j], score
                        )
            result = df[keep_mask].reset_index(drop=True)
        else:
            # Упрощённая дедупликация: удаляем строки с полностью совпадающими именами
            result = df.drop_duplicates(
                subset=["name"] if "name" in df.columns else None
            ).reset_index(drop=True)

        removed = len(df) - len(result)
        self._stats["duplicates_removed"] = removed
        logger.info("deduplicate: удалено %d дублей, осталось %d записей", removed, len(result))
        return result

    def get_stats(self) -> dict:
        """
        Возвращает статистику обработки.

        Returns:
            Словарь с количеством нормализованных записей и дублей.
        """
        return self._stats.copy()
