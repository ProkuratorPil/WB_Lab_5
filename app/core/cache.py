"""
Модуль для работы с Redis кешем.
Реализует паттерн Cache-Aside с явным управлением ключами и TTL.
При недоступности Redis приложение продолжает работать (degradation).
"""
import json
import logging
from typing import Optional, Any
from redis import Redis, ConnectionError, TimeoutError
from app.core.config import settings

logger = logging.getLogger(__name__)


class CacheService:
    """Сервис для работы с Redis кешем."""

    def __init__(self):
        self._client: Optional[Redis] = None
        self._connected = False
        self._connect()

    def _connect(self) -> None:
        """Устанавливает соединение с Redis."""
        try:
            self._client = Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                password=settings.REDIS_PASSWORD or None,
                decode_responses=True,
                socket_connect_timeout=3,
                socket_timeout=3,
                health_check_interval=30,
            )
            self._client.ping()
            self._connected = True
            logger.info("Redis connection established successfully")
        except (ConnectionError, TimeoutError, Exception) as exc:
            self._connected = False
            self._client = None
            logger.warning(f"Redis connection failed: {exc}. Cache is disabled.")

    def _ensure_connection(self) -> bool:
        """Проверяет и при необходимости восстанавливает соединение."""
        if not self._connected or self._client is None:
            self._connect()
        return self._connected

    def get(self, key: str) -> Optional[Any]:
        """
        Получает значение из кеша по ключу.

        Returns:
            Распарсенный JSON объект или None при отсутствии/ошибке.
        """
        if not self._ensure_connection():
            return None
        try:
            raw = self._client.get(key)
            if raw is None:
                return None
            return json.loads(raw)
        except Exception as exc:
            logger.warning(f"Redis GET error for key {key}: {exc}")
            return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """
        Сохраняет значение в кеш с TTL.

        Args:
            key: Ключ кеша.
            value: Значение (будет сериализовано в JSON).
            ttl: Время жизни в секундах. По умолчанию CACHE_TTL_DEFAULT.

        Returns:
            True если операция успешна.
        """
        if not self._ensure_connection():
            return False
        try:
            serialized = json.dumps(value, default=str)
            expire = ttl if ttl is not None else settings.CACHE_TTL_DEFAULT
            self._client.setex(key, expire, serialized)
            return True
        except Exception as exc:
            logger.warning(f"Redis SET error for key {key}: {exc}")
            return False

    def delete(self, key: str) -> bool:
        """
        Удаляет ключ из кеша.

        Returns:
            True если операция успешна.
        """
        if not self._ensure_connection():
            return False
        try:
            self._client.delete(key)
            return True
        except Exception as exc:
            logger.warning(f"Redis DEL error for key {key}: {exc}")
            return False

    def delete_by_pattern(self, pattern: str) -> bool:
        """
        Удаляет ключи по паттерну (использует SCAN + UNLINK для безопасности).

        Args:
            pattern: Шаблон ключа (например, "wp:users:list:*").

        Returns:
            True если операция успешна.
        """
        if not self._ensure_connection():
            return False
        try:
            cursor = 0
            while True:
                cursor, keys = self._client.scan(cursor=cursor, match=pattern, count=100)
                if keys:
                    self._client.unlink(*keys)
                if cursor == 0:
                    break
            return True
        except Exception as exc:
            logger.warning(f"Redis DELETE_BY_PATTERN error for pattern {pattern}: {exc}")
            return False

    def is_healthy(self) -> bool:
        """Проверяет доступность Redis."""
        return self._ensure_connection()


# Глобальный экземпляр сервиса кеша
cache_service = CacheService()
