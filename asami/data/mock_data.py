"""
Генератор фиктивных демонстрационных данных по административным округам Москвы.
Данные реалистичны, но не являются официальной статистикой.
"""

import logging
import random
from typing import Any

import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)

# Фиксируем seed для воспроизводимости
random.seed(42)
np.random.seed(42)


# ── Данные по 12 административным округам Москвы ────────────────────────────
DISTRICTS_RAW: list[dict[str, Any]] = [
    # ЦАО: высокая плотность ~5.8 (исторически развитый центр)
    {
        "id": 1,
        "name": "ЦАО",
        "full_name": "Центральный административный округ",
        "area_km2": 66.2,
        "population": 771606,
        "lat": 55.7558,
        "lon": 37.6173,
        "hospitals": 25,
        "polyclinics": 228,
        "ambulatory": 145,
        "specialized": 50,
    },
    # САО: средняя плотность ~4.5
    {
        "id": 2,
        "name": "САО",
        "full_name": "Северный административный округ",
        "area_km2": 87.3,
        "population": 1121871,
        "lat": 55.8500,
        "lon": 37.5200,
        "hospitals": 18,
        "polyclinics": 278,
        "ambulatory": 148,
        "specialized": 61,
    },
    # СВАО: средняя плотность ~3.9
    {
        "id": 3,
        "name": "СВАО",
        "full_name": "Северо-Восточный административный округ",
        "area_km2": 106.5,
        "population": 1370775,
        "lat": 55.8700,
        "lon": 37.6800,
        "hospitals": 20,
        "polyclinics": 305,
        "ambulatory": 168,
        "specialized": 42,
    },
    # ВАО: ниже среднего ~3.4
    {
        "id": 4,
        "name": "ВАО",
        "full_name": "Восточный административный округ",
        "area_km2": 151.0,
        "population": 1479328,
        "lat": 55.7800,
        "lon": 37.8100,
        "hospitals": 19,
        "polyclinics": 298,
        "ambulatory": 155,
        "specialized": 36,
    },
    # ЮВАО: на пороге ~3.1
    {
        "id": 5,
        "name": "ЮВАО",
        "full_name": "Юго-Восточный административный округ",
        "area_km2": 117.0,
        "population": 1242245,
        "lat": 55.7000,
        "lon": 37.7700,
        "hospitals": 16,
        "polyclinics": 224,
        "ambulatory": 118,
        "specialized": 28,
    },
    # ЮАО: средняя плотность ~3.7
    {
        "id": 6,
        "name": "ЮАО",
        "full_name": "Южный административный округ",
        "area_km2": 130.6,
        "population": 1739821,
        "lat": 55.6400,
        "lon": 37.6200,
        "hospitals": 22,
        "polyclinics": 362,
        "ambulatory": 195,
        "specialized": 65,
    },
    # ЮЗАО: выше среднего ~4.1
    {
        "id": 7,
        "name": "ЮЗАО",
        "full_name": "Юго-Западный административный округ",
        "area_km2": 106.8,
        "population": 1399801,
        "lat": 55.6600,
        "lon": 37.5200,
        "hospitals": 20,
        "polyclinics": 320,
        "ambulatory": 178,
        "specialized": 56,
    },
    # ЗАО: средняя плотность ~3.6
    {
        "id": 8,
        "name": "ЗАО",
        "full_name": "Западный административный округ",
        "area_km2": 132.0,
        "population": 1363913,
        "lat": 55.7400,
        "lon": 37.3900,
        "hospitals": 19,
        "polyclinics": 281,
        "ambulatory": 148,
        "specialized": 45,
    },
    # СЗАО: выше среднего ~4.0
    {
        "id": 9,
        "name": "СЗАО",
        "full_name": "Северо-Западный административный округ",
        "area_km2": 106.9,
        "population": 970780,
        "lat": 55.8200,
        "lon": 37.4000,
        "hospitals": 15,
        "polyclinics": 228,
        "ambulatory": 118,
        "specialized": 27,
    },
    # ЗеАО: выше порога ~3.2 (компактный округ, хорошая обеспеченность)
    {
        "id": 10,
        "name": "ЗеАО",
        "full_name": "Зеленоградский административный округ",
        "area_km2": 37.2,
        "population": 262584,
        "lat": 55.9900,
        "lon": 37.1900,
        "hospitals": 6,
        "polyclinics": 52,
        "ambulatory": 22,
        "specialized": 4,
    },
    # НАО: ниже порога ~2.5 (активно застраивающийся округ)
    {
        "id": 11,
        "name": "НАО",
        "full_name": "Новомосковский административный округ",
        "area_km2": 352.2,
        "population": 369619,
        "lat": 55.5200,
        "lon": 37.2800,
        "hospitals": 7,
        "polyclinics": 58,
        "ambulatory": 22,
        "specialized": 6,
    },
    # ТиНАО: критически низкая плотность ~1.9 (большая территория, малое население)
    {
        "id": 12,
        "name": "ТиНАО",
        "full_name": "Троицкий и Новомосковский административный округ",
        "area_km2": 1459.1,
        "population": 296416,
        "lat": 55.3600,
        "lon": 37.2800,
        "hospitals": 5,
        "polyclinics": 36,
        "ambulatory": 12,
        "specialized": 3,
    },
]

# ── Конкретные МО (50 записей) ───────────────────────────────────────────────
MEDICAL_OBJECTS_RAW: list[dict[str, Any]] = [
    # ЦАО
    {"id": 1, "name": "ГКБ №1 им. Н.И. Пирогова", "type": "hospital", "district": "ЦАО",
     "address": "Ленинский пр-т, 8", "lat": 55.7270, "lon": 37.5810, "source": "официальный", "confidence_score": 0.98},
    {"id": 2, "name": "Городская поликлиника №5", "type": "polyclinic", "district": "ЦАО",
     "address": "ул. Арбат, 28", "lat": 55.7500, "lon": 37.5920, "source": "официальный", "confidence_score": 0.97},
    {"id": 3, "name": "НМИЦ онкологии им. Блохина", "type": "specialized", "district": "ЦАО",
     "address": "Каширское ш., 23", "lat": 55.6590, "lon": 37.6490, "source": "официальный", "confidence_score": 0.99},
    {"id": 4, "name": "Клиника «Медицина»", "type": "polyclinic", "district": "ЦАО",
     "address": "2-й Тверской-Ямской пер., 10", "lat": 55.7730, "lon": 37.5830, "source": "OSM", "confidence_score": 0.85},
    {"id": 5, "name": "Амбулатория Пресненского района", "type": "ambulatory", "district": "ЦАО",
     "address": "Мал. Конюшковская ул., 8", "lat": 55.7620, "lon": 37.5760, "source": "OSM", "confidence_score": 0.82},

    # САО
    {"id": 6, "name": "ГКБ №50 им. С.И. Спасокукоцкого", "type": "hospital", "district": "САО",
     "address": "Вучетича ул., 21", "lat": 55.8250, "lon": 37.5640, "source": "официальный", "confidence_score": 0.96},
    {"id": 7, "name": "Поликлиника №114 (Войковский р-н)", "type": "polyclinic", "district": "САО",
     "address": "Большая Академическая ул., 6", "lat": 55.8410, "lon": 37.5200, "source": "официальный", "confidence_score": 0.95},
    {"id": 8, "name": "Перинатальный центр ГБУЗ «ГКБ №67»", "type": "specialized", "district": "САО",
     "address": "Саляма Адиля ул., 2", "lat": 55.8350, "lon": 37.4900, "source": "официальный", "confidence_score": 0.97},
    {"id": 9, "name": "Амбулатория «Ховрино»", "type": "ambulatory", "district": "САО",
     "address": "Фестивальная ул., 35", "lat": 55.8760, "lon": 37.4740, "source": "OSM", "confidence_score": 0.78},
    {"id": 10, "name": "Поликлиника №211 Северного АО", "type": "polyclinic", "district": "САО",
     "address": "Клязьминская ул., 12", "lat": 55.8610, "lon": 37.5350, "source": "официальный", "confidence_score": 0.93},

    # СВАО
    {"id": 11, "name": "ГКБ №40 «Коммунарка»", "type": "hospital", "district": "СВАО",
     "address": "Сосенское пос., 5", "lat": 55.8760, "lon": 37.5080, "source": "официальный", "confidence_score": 0.98},
    {"id": 12, "name": "ДГП №32 (Ростокино)", "type": "polyclinic", "district": "СВАО",
     "address": "Ростокинская ул., 5", "lat": 55.8420, "lon": 37.6680, "source": "официальный", "confidence_score": 0.94},
    {"id": 13, "name": "Лосиноостровская поликлиника №96", "type": "polyclinic", "district": "СВАО",
     "address": "Ярославское ш., 116", "lat": 55.8700, "lon": 37.6900, "source": "OSM", "confidence_score": 0.87},
    {"id": 14, "name": "Онкологический диспансер №3", "type": "specialized", "district": "СВАО",
     "address": "Дурова ул., 24", "lat": 55.7880, "lon": 37.6220, "source": "официальный", "confidence_score": 0.96},
    {"id": 15, "name": "Амбулатория «Бабушкинская»", "type": "ambulatory", "district": "СВАО",
     "address": "Ярославское ш., 48А", "lat": 55.8580, "lon": 37.6620, "source": "OSM", "confidence_score": 0.81},

    # ВАО
    {"id": 16, "name": "ГКБ №36", "type": "hospital", "district": "ВАО",
     "address": "Фортунатовская ул., 1", "lat": 55.7820, "lon": 37.7350, "source": "официальный", "confidence_score": 0.95},
    {"id": 17, "name": "Поликлиника №54 (Перово)", "type": "polyclinic", "district": "ВАО",
     "address": "Зелёный пр-т, 22", "lat": 55.7640, "lon": 37.7930, "source": "официальный", "confidence_score": 0.93},
    {"id": 18, "name": "МФЦ здоровья «Измайлово»", "type": "specialized", "district": "ВАО",
     "address": "Измайловский пр-т, 43", "lat": 55.7890, "lon": 37.8230, "source": "OSM", "confidence_score": 0.84},
    {"id": 19, "name": "ДГП №46 «Новогиреево»", "type": "polyclinic", "district": "ВАО",
     "address": "Кусковская ул., 19", "lat": 55.7510, "lon": 37.8060, "source": "официальный", "confidence_score": 0.91},
    {"id": 20, "name": "Амбулатория «Богородское»", "type": "ambulatory", "district": "ВАО",
     "address": "Краснобогатырская ул., 2", "lat": 55.8050, "lon": 37.7280, "source": "OSM", "confidence_score": 0.79},

    # ЮВАО
    {"id": 21, "name": "ГКБ №13", "type": "hospital", "district": "ЮВАО",
     "address": "Велозаводская ул., 1/1", "lat": 55.7270, "lon": 37.6930, "source": "официальный", "confidence_score": 0.97},
    {"id": 22, "name": "Поликлиника №71 (Люблино)", "type": "polyclinic", "district": "ЮВАО",
     "address": "Люблинская ул., 37", "lat": 55.6790, "lon": 37.7580, "source": "официальный", "confidence_score": 0.94},
    {"id": 23, "name": "Амбулатория «Текстильщики»", "type": "ambulatory", "district": "ЮВАО",
     "address": "Волгоградский пр-т, 104", "lat": 55.7060, "lon": 37.7430, "source": "OSM", "confidence_score": 0.80},
    {"id": 24, "name": "Поликлиника №165 (Марьино)", "type": "polyclinic", "district": "ЮВАО",
     "address": "Новочеркасский б-р, 6", "lat": 55.6650, "lon": 37.7390, "source": "официальный", "confidence_score": 0.92},
    {"id": 25, "name": "Стоматологическая поликлиника №40", "type": "specialized", "district": "ЮВАО",
     "address": "Люблинская ул., 72", "lat": 55.6830, "lon": 37.7440, "source": "OSM", "confidence_score": 0.86},

    # ЮАО
    {"id": 26, "name": "ГКБ №79", "type": "hospital", "district": "ЮАО",
     "address": "Ленинский пр-т, 78", "lat": 55.6760, "lon": 37.5570, "source": "официальный", "confidence_score": 0.96},
    {"id": 27, "name": "Поликлиника №116 (Нагорный)", "type": "polyclinic", "district": "ЮАО",
     "address": "Болотниковская ул., 5", "lat": 55.6590, "lon": 37.5990, "source": "официальный", "confidence_score": 0.93},
    {"id": 28, "name": "ЦКБ «Нагатино»", "type": "specialized", "district": "ЮАО",
     "address": "Нагатинская наб., 12", "lat": 55.6710, "lon": 37.6350, "source": "официальный", "confidence_score": 0.95},
    {"id": 29, "name": "Амбулатория «Бирюлёво Западное»", "type": "ambulatory", "district": "ЮАО",
     "address": "Загорьевская ул., 6А", "lat": 55.6050, "lon": 37.5950, "source": "OSM", "confidence_score": 0.76},
    {"id": 30, "name": "Детская поликлиника №132 (Чертаново)", "type": "polyclinic", "district": "ЮАО",
     "address": "Чертановская ул., 9А", "lat": 55.6370, "lon": 37.6080, "source": "официальный", "confidence_score": 0.90},

    # ЮЗАО
    {"id": 31, "name": "ГКБ №64", "type": "hospital", "district": "ЮЗАО",
     "address": "Вавилова ул., 61", "lat": 55.6820, "lon": 37.5530, "source": "официальный", "confidence_score": 0.97},
    {"id": 32, "name": "Поликлиника №121 (Ясенево)", "type": "polyclinic", "district": "ЮЗАО",
     "address": "Голубинская ул., 3А", "lat": 55.6110, "lon": 37.5150, "source": "официальный", "confidence_score": 0.94},
    {"id": 33, "name": "НМИЦ хирургии им. Вишневского", "type": "specialized", "district": "ЮЗАО",
     "address": "Большая Серпуховская ул., 27", "lat": 55.7130, "lon": 37.6300, "source": "официальный", "confidence_score": 0.99},
    {"id": 34, "name": "Амбулатория «Черёмушки»", "type": "ambulatory", "district": "ЮЗАО",
     "address": "Гарибальди ул., 10", "lat": 55.6690, "lon": 37.5210, "source": "OSM", "confidence_score": 0.82},
    {"id": 35, "name": "Поликлиника №99 (Коньково)", "type": "polyclinic", "district": "ЮЗАО",
     "address": "Профсоюзная ул., 126", "lat": 55.6290, "lon": 37.5380, "source": "официальный", "confidence_score": 0.91},

    # ЗАО
    {"id": 36, "name": "ГКБ №67 им. Ворохобова", "type": "hospital", "district": "ЗАО",
     "address": "Саляма Адиля ул., 2", "lat": 55.7490, "lon": 37.3790, "source": "официальный", "confidence_score": 0.97},
    {"id": 37, "name": "Поликлиника №209 (Можайский)", "type": "polyclinic", "district": "ЗАО",
     "address": "Можайское ш., 12", "lat": 55.7460, "lon": 37.3430, "source": "официальный", "confidence_score": 0.92},
    {"id": 38, "name": "Амбулатория «Фили-Давыдково»", "type": "ambulatory", "district": "ЗАО",
     "address": "Кастанаевская ул., 31", "lat": 55.7350, "lon": 37.4010, "source": "OSM", "confidence_score": 0.80},
    {"id": 39, "name": "Поликлиника №83 (Кунцево)", "type": "polyclinic", "district": "ЗАО",
     "address": "Рублёвское ш., 46", "lat": 55.7580, "lon": 37.3360, "source": "официальный", "confidence_score": 0.93},
    {"id": 40, "name": "Консультативно-диагностический центр №7", "type": "specialized", "district": "ЗАО",
     "address": "Озёрная ул., 10", "lat": 55.7010, "lon": 37.3840, "source": "официальный", "confidence_score": 0.95},

    # СЗАО
    {"id": 41, "name": "ГКБ №52", "type": "hospital", "district": "СЗАО",
     "address": "Пехотная ул., 3", "lat": 55.8090, "lon": 37.4290, "source": "официальный", "confidence_score": 0.96},
    {"id": 42, "name": "Поликлиника №180 (Митино)", "type": "polyclinic", "district": "СЗАО",
     "address": "Митинская ул., 44", "lat": 55.8550, "lon": 37.3840, "source": "официальный", "confidence_score": 0.93},
    {"id": 43, "name": "Амбулатория «Строгино»", "type": "ambulatory", "district": "СЗАО",
     "address": "Строгинский б-р, 14", "lat": 55.8040, "lon": 37.3670, "source": "OSM", "confidence_score": 0.78},

    # ЗеАО
    {"id": 44, "name": "Зеленоградская городская больница №3", "type": "hospital", "district": "ЗеАО",
     "address": "Зеленоград, 1-й Западный пр-д, 2", "lat": 55.9890, "lon": 37.2060, "source": "официальный", "confidence_score": 0.95},
    {"id": 45, "name": "Поликлиника №201 (Зеленоград)", "type": "polyclinic", "district": "ЗеАО",
     "address": "Зеленоград, Панфиловский пр-т, 1446", "lat": 55.9750, "lon": 37.1970, "source": "официальный", "confidence_score": 0.94},

    # НАО
    {"id": 46, "name": "ГКБ Коммунарка (НАО)", "type": "hospital", "district": "НАО",
     "address": "пос. Коммунарка, ул. Сосенский Стан, 8", "lat": 55.5560, "lon": 37.3700, "source": "официальный", "confidence_score": 0.97},
    {"id": 47, "name": "Поликлиника НАО «Щербинка»", "type": "polyclinic", "district": "НАО",
     "address": "г. Щербинка, ул. Южная, 8", "lat": 55.5000, "lon": 37.5600, "source": "официальный", "confidence_score": 0.90},

    # ТиНАО
    {"id": 48, "name": "Троицкая городская больница", "type": "hospital", "district": "ТиНАО",
     "address": "г. Троицк, ул. Октябрьская, 12", "lat": 55.4820, "lon": 37.2940, "source": "официальный", "confidence_score": 0.93},
    {"id": 49, "name": "Поликлиника ТиНАО «Троицк»", "type": "polyclinic", "district": "ТиНАО",
     "address": "г. Троицк, Октябрьский пр-т, 4", "lat": 55.4860, "lon": 37.3070, "source": "официальный", "confidence_score": 0.91},
    {"id": 50, "name": "Амбулатория «Вороново»", "type": "ambulatory", "district": "ТиНАО",
     "address": "п. Вороново, ул. Пушкина, 2", "lat": 55.3460, "lon": 37.0940, "source": "OSM", "confidence_score": 0.74},
]


def get_districts_dataframe() -> pd.DataFrame:
    """
    Формирует DataFrame с данными по округам и рассчитывает производные метрики.

    Returns:
        DataFrame с колонками: id, name, full_name, area_km2, population,
        lat, lon, hospitals, polyclinics, ambulatory, specialized,
        total_mo, density, accessibility_score, white_spots_count, status.
    """
    logger.debug("Формирование DataFrame округов из mock-данных")
    df = pd.DataFrame(DISTRICTS_RAW)

    # Итоговое количество МО
    df["total_mo"] = (
        df["hospitals"] + df["polyclinics"] + df["ambulatory"] + df["specialized"]
    )

    # Плотность МО на 10 000 жителей
    df["density"] = (df["total_mo"] / (df["population"] / 10_000)).round(2)

    # Нормализованная оценка доступности [0, 1]
    max_density = df["density"].max()
    min_area = df["area_km2"].min()
    df["accessibility_score"] = (
        0.6 * (df["density"] / max_density)
        + 0.4 * (min_area / df["area_km2"]).clip(0, 1)
    ).round(3)

    # Количество белых пятен (зон без МО в радиусе 1 км) — модель
    df["white_spots_count"] = (
        (df["area_km2"] / df["total_mo"] * 0.8).astype(int).clip(lower=0)
    )

    logger.info("Округа загружены: %d строк", len(df))
    return df


def get_medical_objects_dataframe() -> pd.DataFrame:
    """
    Формирует DataFrame со списком конкретных медицинских организаций.

    Returns:
        DataFrame с 50 записями МО.
    """
    logger.debug("Формирование DataFrame медицинских организаций")
    df = pd.DataFrame(MEDICAL_OBJECTS_RAW)
    logger.info("МО загружены: %d записей", len(df))
    return df


def get_metrics_history(district_name: str, months: int = 6) -> pd.DataFrame:
    """
    Генерирует историю метрик для округа за последние N месяцев.

    Args:
        district_name: Название округа (аббревиатура, например 'ЦАО').
        months: Количество месяцев истории.

    Returns:
        DataFrame с колонками: month, density, accessibility_score, total_mo.
    """
    logger.debug("Генерация истории метрик: округ=%s, месяцев=%d", district_name, months)

    districts_df = get_districts_dataframe()
    row = districts_df[districts_df["name"] == district_name]
    if row.empty:
        logger.warning("Округ '%s' не найден, возвращаем пустой DataFrame", district_name)
        return pd.DataFrame()

    base_density = float(row["density"].iloc[0])
    base_access = float(row["accessibility_score"].iloc[0])
    base_mo = int(row["total_mo"].iloc[0])

    dates = pd.date_range(end=pd.Timestamp.now(), periods=months, freq="ME")
    history = []
    for i, date in enumerate(dates):
        noise = 1 + np.random.uniform(-0.05, 0.05)
        history.append({
            "month": date.strftime("%Y-%m"),
            "density": round(base_density * noise, 2),
            "accessibility_score": round(min(1.0, base_access * noise), 3),
            "total_mo": max(1, base_mo + np.random.randint(-2, 3)),
        })

    return pd.DataFrame(history)
