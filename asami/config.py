"""
Конфигурация системы АСАМИ.
Содержит параметры подключения к БД, цветовые схемы и системные константы.
"""

import logging
import os
from dotenv import load_dotenv

load_dotenv()

# ── Параметры подключения к PostgreSQL/PostGIS ──────────────────────────────
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", 5432)),
    "database": os.getenv("DB_NAME", "asami_db"),
    "user": os.getenv("DB_USER", "asami_user"),
    "password": os.getenv("DB_PASSWORD", "asami_pass"),
}

DB_URL = (
    f"postgresql://{DB_CONFIG['user']}:{DB_CONFIG['password']}"
    f"@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}"
)

# ── Параметры системы ────────────────────────────────────────────────────────
APP_TITLE = "АСАМИ — Анализ медицинской инфраструктуры"
APP_SUBTITLE = "Автоматизированная система анализа медицинских организаций города"
APP_VERSION = "1.0.0-demo"

# Доступные города
CITIES = ["Москва"]

# Порог плотности МО по умолчанию (МО / 10 000 жителей)
DEFAULT_DENSITY_THRESHOLD = 3.0
DENSITY_THRESHOLD_MIN = 0.5
DENSITY_THRESHOLD_MAX = 5.0
DENSITY_THRESHOLD_STEP = 0.1

# Типы медицинских организаций
MO_TYPES = {
    "all": "Все типы",
    "hospital": "Больницы",
    "polyclinic": "Поликлиники",
    "ambulatory": "Амбулатории",
    "specialized": "Специализированные центры",
}

# ── Цветовая схема ───────────────────────────────────────────────────────────
COLORS = {
    "primary": "#1B3A6B",
    "accent": "#2563EB",
    "success": "#16A34A",
    "warning": "#D97706",
    "danger": "#DC2626",
    "bg_light": "#F0F4F8",
}

# Пороги для статусов округов
STATUS_HIGH = 0.7       # accessibility_score > HIGH → "Норма"
STATUS_MEDIUM = 0.4     # accessibility_score > MEDIUM → "Внимание"

# ── Координаты карты ─────────────────────────────────────────────────────────
MAP_CENTER = [55.7558, 37.6173]   # центр Москвы
MAP_ZOOM = 10

# Bounding box Москвы для геокодирования
MOSCOW_BBOX = {
    "lat_min": 55.55,
    "lat_max": 55.90,
    "lon_min": 37.35,
    "lon_max": 37.85,
}

# ── Логирование ──────────────────────────────────────────────────────────────
LOG_LEVEL = logging.INFO
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"

logging.basicConfig(level=LOG_LEVEL, format=LOG_FORMAT)
