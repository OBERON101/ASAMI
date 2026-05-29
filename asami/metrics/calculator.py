"""
Модуль расчёта метрик медицинской инфраструктуры.

Реализует вычисление ключевых показателей:
- density: плотность МО на 10 000 жителей
- accessibility_score: нормализованная оценка доступности
- white_spots: зоны дефицита медицинской помощи
"""

import logging
from typing import Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class MetricsEngine:
    """
    Движок расчёта метрик медицинской инфраструктуры города.

    Все методы работают как со скалярными значениями, так и с DataFrame.
    При невалидных входных данных возвращают безопасные значения по умолчанию.
    """

    def __init__(self) -> None:
        """Инициализация движка метрик."""
        logger.info("MetricsEngine инициализирован")

    def calculate_density(self, mo_count: int, population: int) -> float:
        """
        Вычисляет плотность МО на 10 000 жителей.

        Args:
            mo_count: Количество МО в округе.
            population: Численность населения округа.

        Returns:
            Плотность МО (МО / 10 000 жителей). 0.0 при population == 0.
        """
        if population <= 0:
            logger.warning("calculate_density: population=%d, возвращаем 0.0", population)
            return 0.0

        density = mo_count / (population / 10_000)
        logger.debug(
            "calculate_density: mo_count=%d, population=%d → %.4f",
            mo_count, population, density
        )
        return round(density, 4)

    def calculate_accessibility(self, district_data: dict) -> float:
        """
        Вычисляет нормализованную оценку доступности медицинской помощи.

        Формула: 0.5 * density_norm + 0.3 * mo_variety_norm + 0.2 * area_correction
        где:
          - density_norm: нормированная плотность (отн. максимума по городу)
          - mo_variety_norm: разнообразие типов МО / 4 (макс. число типов)
          - area_correction: штраф за большую площадь округа

        Args:
            district_data: Словарь с ключами: density, hospitals, polyclinics,
                           ambulatory, specialized, area_km2.

        Returns:
            Оценка доступности в диапазоне [0.0, 1.0].
        """
        density = float(district_data.get("density", 0.0))
        hospitals = int(district_data.get("hospitals", 0))
        polyclinics = int(district_data.get("polyclinics", 0))
        ambulatory = int(district_data.get("ambulatory", 0))
        specialized = int(district_data.get("specialized", 0))
        area = float(district_data.get("area_km2", 100.0))

        # Разнообразие типов МО (0..1)
        variety = sum([
            hospitals > 0,
            polyclinics > 0,
            ambulatory > 0,
            specialized > 0,
        ]) / 4.0

        # Штраф за большую площадь (обратная нормализация, ln-scale)
        # Большой округ → меньший балл доступности (сложнее добраться)
        area_penalty = max(0.0, 1.0 - np.log1p(area) / np.log1p(1500))

        # Нормализация плотности (ожидаемый максимум ~7)
        density_norm = min(1.0, density / 7.0)

        score = 0.5 * density_norm + 0.3 * variety + 0.2 * area_penalty
        score = round(float(np.clip(score, 0.0, 1.0)), 4)

        logger.debug(
            "calculate_accessibility: density=%.2f, variety=%.2f, area_penalty=%.2f → %.4f",
            density, variety, area_penalty, score
        )
        return score

    def find_white_spots(
        self,
        districts_df: pd.DataFrame,
        threshold: float,
    ) -> list[str]:
        """
        Находит округа с дефицитом МО (density < threshold).

        Args:
            districts_df: DataFrame с колонкой density и name.
            threshold: Пороговое значение плотности.

        Returns:
            Список названий округов-"белых пятен" по возрастанию density.
        """
        if "density" not in districts_df.columns or "name" not in districts_df.columns:
            logger.error("find_white_spots: отсутствуют колонки density или name")
            return []

        mask = districts_df["density"] < threshold
        spots = (
            districts_df[mask]
            .sort_values("density")["name"]
            .tolist()
        )
        logger.info(
            "find_white_spots: порог=%.1f, найдено %d округов", threshold, len(spots)
        )
        return spots

    def calculate_all(self, districts_df: pd.DataFrame) -> pd.DataFrame:
        """
        Добавляет все рассчитанные метрики к DataFrame округов.

        Пересчитывает density и accessibility_score на основе текущих данных.

        Args:
            districts_df: DataFrame с колонками population, total_mo, area_km2
                          hospitals, polyclinics, ambulatory, specialized.

        Returns:
            DataFrame с добавленными/обновлёнными колонками:
            density, accessibility_score, white_spots_count, status.
        """
        result = districts_df.copy()

        # Пересчёт density
        result["density"] = result.apply(
            lambda r: self.calculate_density(
                int(r.get("total_mo", 0)),
                int(r.get("population", 1)),
            ),
            axis=1,
        )

        # Пересчёт accessibility_score
        result["accessibility_score"] = result.apply(
            lambda r: self.calculate_accessibility(r.to_dict()),
            axis=1,
        )

        # Примерный подсчёт белых пятен: площадь / плотность МО
        result["white_spots_count"] = (
            (result["area_km2"] / result["total_mo"].clip(lower=1) * 0.8)
            .astype(int)
            .clip(lower=0)
        )

        logger.info("calculate_all: метрики пересчитаны для %d округов", len(result))
        return result

    def get_summary_stats(self, districts_df: pd.DataFrame) -> dict:
        """
        Возвращает сводную статистику по метрикам всех округов.

        Args:
            districts_df: DataFrame с колонками density, accessibility_score,
                          total_mo, white_spots_count.

        Returns:
            Словарь с ключами:
              density_{mean,min,max}, accessibility_{mean,min,max},
              total_mo_{sum,mean}, white_spots_total.
        """
        stats: dict = {}

        for col, key in [
            ("density", "density"),
            ("accessibility_score", "accessibility"),
        ]:
            if col in districts_df.columns:
                stats[f"{key}_mean"] = round(float(districts_df[col].mean()), 3)
                stats[f"{key}_min"]  = round(float(districts_df[col].min()),  3)
                stats[f"{key}_max"]  = round(float(districts_df[col].max()),  3)
            else:
                stats.update({f"{key}_mean": 0, f"{key}_min": 0, f"{key}_max": 0})

        if "total_mo" in districts_df.columns:
            stats["total_mo_sum"]  = int(districts_df["total_mo"].sum())
            stats["total_mo_mean"] = round(float(districts_df["total_mo"].mean()), 1)
        else:
            stats.update({"total_mo_sum": 0, "total_mo_mean": 0})

        if "white_spots_count" in districts_df.columns:
            stats["white_spots_total"] = int(districts_df["white_spots_count"].sum())
        else:
            stats["white_spots_total"] = 0

        logger.info("get_summary_stats: %s", stats)
        return stats
