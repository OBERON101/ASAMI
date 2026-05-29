"""
Модуль подключения к базе данных PostgreSQL/PostGIS.

Обеспечивает безопасное соединение с БД через psycopg2/SQLAlchemy,
обрабатывает отсутствие подключения и автоматически переключается
на mock-данные при недоступности PostgreSQL.
"""

import logging
from contextlib import contextmanager
from typing import Any, Generator, Optional

import pandas as pd

try:
    import psycopg2
    import psycopg2.extras
    from sqlalchemy import create_engine, text
    from sqlalchemy.engine import Engine
    PSYCOPG2_AVAILABLE = True
except ImportError:
    PSYCOPG2_AVAILABLE = False

from config import DB_CONFIG, DB_URL

logger = logging.getLogger(__name__)


class DatabaseConnection:
    """
    Класс управления подключением к PostgreSQL/PostGIS.

    Поддерживает контекстный менеджер (with DatabaseConnection() as db:).
    При недоступности БД не выбрасывает исключение, а устанавливает
    флаг is_connected = False.
    """

    def __init__(self) -> None:
        """Инициализация без немедленного подключения."""
        self._connection: Optional[Any] = None
        self._engine: Optional[Any] = None
        self.is_connected: bool = False
        self.error_message: str = ""

    def connect(self) -> bool:
        """
        Устанавливает подключение к PostgreSQL.

        Returns:
            True если подключение успешно, False в противном случае.
        """
        if not PSYCOPG2_AVAILABLE:
            self.error_message = "psycopg2 не установлен"
            logger.warning("psycopg2 недоступен, работа в режиме mock-данных")
            return False

        try:
            logger.info("Попытка подключения к БД: %s:%d/%s",
                        DB_CONFIG["host"], DB_CONFIG["port"], DB_CONFIG["database"])

            self._connection = psycopg2.connect(
                host=DB_CONFIG["host"],
                port=DB_CONFIG["port"],
                database=DB_CONFIG["database"],
                user=DB_CONFIG["user"],
                password=DB_CONFIG["password"],
                connect_timeout=3,          # тайм-аут 3 секунды
            )
            self._engine = create_engine(DB_URL, pool_pre_ping=True)
            self.is_connected = True
            logger.info("Подключение к БД установлено успешно")
            return True

        except Exception as exc:
            self.error_message = str(exc)
            self.is_connected = False
            logger.warning("БД недоступна (%s), переключение на mock-данные", exc)
            return False

    def disconnect(self) -> None:
        """Закрывает подключение к БД."""
        if self._connection is not None:
            try:
                self._connection.close()
                logger.info("Подключение к БД закрыто")
            except Exception as exc:
                logger.error("Ошибка при закрытии соединения: %s", exc)
            finally:
                self._connection = None
                self.is_connected = False

        if self._engine is not None:
            try:
                self._engine.dispose()
            except Exception as exc:
                logger.error("Ошибка при закрытии Engine: %s", exc)
            finally:
                self._engine = None

    def execute_query(self, sql: str, params: Optional[dict] = None) -> list[dict]:
        """
        Выполняет SQL-запрос и возвращает список строк в виде словарей.

        Args:
            sql: Текст SQL-запроса.
            params: Параметры запроса для защиты от SQL-инъекций.

        Returns:
            Список словарей с результатами или пустой список при ошибке.
        """
        if not self.is_connected or self._connection is None:
            logger.warning("execute_query вызван без активного соединения")
            return []

        try:
            logger.debug("SQL: %s | params: %s", sql.strip()[:120], params)
            with self._connection.cursor(
                cursor_factory=psycopg2.extras.RealDictCursor
            ) as cursor:
                cursor.execute(sql, params or {})
                rows = cursor.fetchall()
                logger.debug("Получено строк: %d", len(rows))
                return [dict(row) for row in rows]

        except Exception as exc:
            logger.error("Ошибка выполнения запроса: %s", exc)
            self._connection.rollback()
            return []

    def get_dataframe(self, sql: str, params: Optional[dict] = None) -> pd.DataFrame:
        """
        Выполняет SQL-запрос и возвращает результат как pandas DataFrame.

        Args:
            sql: Текст SQL-запроса.
            params: Параметры запроса.

        Returns:
            DataFrame с результатами или пустой DataFrame при ошибке.
        """
        if not self.is_connected or self._engine is None:
            logger.warning("get_dataframe вызван без активного соединения")
            return pd.DataFrame()

        try:
            logger.debug("SQL→DataFrame: %s", sql.strip()[:120])
            with self._engine.connect() as conn:
                df = pd.read_sql(text(sql), conn, params=params or {})
            logger.debug("DataFrame получен: %d строк × %d колонок", len(df), len(df.columns))
            return df

        except Exception as exc:
            logger.error("Ошибка get_dataframe: %s", exc)
            return pd.DataFrame()

    def __enter__(self) -> "DatabaseConnection":
        """Вход в контекстный менеджер — выполняет подключение."""
        self.connect()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Выход из контекстного менеджера — закрывает соединение."""
        self.disconnect()


@contextmanager
def get_db() -> Generator[DatabaseConnection, None, None]:
    """
    Контекстный менеджер для получения соединения с БД.

    Пример использования:
        with get_db() as db:
            if db.is_connected:
                df = db.get_dataframe("SELECT * FROM districts")

    Yields:
        Экземпляр DatabaseConnection.
    """
    db = DatabaseConnection()
    try:
        db.connect()
        yield db
    finally:
        db.disconnect()


def check_db_status() -> tuple[bool, str]:
    """
    Проверяет доступность БД без сохранения соединения.

    Returns:
        Кортеж (is_available: bool, message: str).
    """
    db = DatabaseConnection()
    connected = db.connect()
    message = "Подключена" if connected else db.error_message
    db.disconnect()
    return connected, message
