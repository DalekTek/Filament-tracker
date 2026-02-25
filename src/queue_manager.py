from typing import Optional, Any, Dict
import json
import aioredis
from datetime import datetime
from pydantic import BaseModel

class Message(BaseModel):
    """Модель сообщения для очереди"""
    user_id: int
    message_text: str
    command: Optional[str]
    timestamp: datetime
    metadata: Dict[str, Any] = {}

class QueueManager:
    def __init__(self, redis_url: str = "redis://localhost"):
        """
        Инициализация менеджера очередей
        :param redis_url: URL для подключения к Redis
        """
        self.redis_url = redis_url
        self._redis: Optional[aioredis.Redis] = None

    async def connect(self) -> None:
        """Установка соединения с Redis"""
        self._redis = await aioredis.from_url(
            self.redis_url,
            encoding="utf-8",
            decode_responses=True
        )

    async def close(self) -> None:
        """Закрытие соединения с Redis"""
        if self._redis:
            await self._redis.close()

    async def push_message(self, message: Message) -> bool:
        """
        Добавление сообщения в очередь
        :param message: Объект сообщения
        :return: Успешность операции
        """
        try:
            # Сериализуем сообщение в JSON
            message_data = message.dict()
            message_data['timestamp'] = message_data['timestamp'].isoformat()
            
            # Добавляем в очередь
            await self._redis.lpush(
                'bot_messages_queue',
                json.dumps(message_data)
            )
            
            # Устанавливаем TTL (время жизни) для сообщения (7 дней)
            await self._redis.expire('bot_messages_queue', 60 * 60 * 24 * 7)
            return True
        except Exception as e:
            print(f"Error pushing message to queue: {e}")
            return False

    async def get_message(self) -> Optional[Message]:
        """
        Получение сообщения из очереди
        :return: Объект сообщения или None
        """
        try:
            # Получаем сообщение из очереди
            message_data = await self._redis.rpop('bot_messages_queue')
            if message_data:
                # Десериализуем JSON
                data = json.loads(message_data)
                data['timestamp'] = datetime.fromisoformat(data['timestamp'])
                return Message(**data)
            return None
        except Exception as e:
            print(f"Error getting message from queue: {e}")
            return None

    async def get_queue_length(self) -> int:
        """
        Получение длины очереди
        :return: Количество сообщений в очереди
        """
        try:
            return await self._redis.llen('bot_messages_queue')
        except Exception:
            return 0