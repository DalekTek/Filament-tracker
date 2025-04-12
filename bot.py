import asyncio
import logging
from datetime import datetime
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message
from config import load_config
from database import Database
from handlers import FilamentHandler
from security import SecurityManager
from queue_manager import QueueManager, Message as QueueMessage
from typing import Any


class MessageMiddleware:
    def __init__(self, bot: 'SecureFilamentBot'):
        self.bot = bot

    async def __call__(
            self,
            handler: callable,
            event: Message,
            data: dict
    ) -> Any:
        return await self.bot.process_message(event)


class SecureFilamentBot:
    def __init__(self):
        # Инициализация логгера
        self.logger = logging.getLogger(__name__)

        # Загрузка конфигурации
        self.config = load_config()

        # Инициализация компонентов
        self.bot = Bot(token=self.config.bot_token)
        self.storage = MemoryStorage()
        self.dp = Dispatcher(storage=self.storage)

        # Инициализация менеджеров
        self.security = SecurityManager()
        self.queue = QueueManager(
            f"redis://{self.config.redis.host}:{self.config.redis.port}"
        )
        self.db = Database(self.config.database.path)

        # Инициализация обработчика команд
        self.handler = FilamentHandler(self.db)

        # Задача для обработки очереди
        self.queue_task = None

    async def process_message(self, message: Message) -> None:
        """Обработка входящего сообщения с учетом безопасности"""
        try:
            # Проверка сессии пользователя
            if not self.security.validate_session(message.from_user.id):
                self.security.create_session(message.from_user.id)

            # Создание объекта сообщения для очереди
            queue_message = QueueMessage(
                user_id=message.from_user.id,
                message_text=message.text or "",
                command=message.text.split()[0] if message.text else None,
                timestamp=datetime.now(),
                metadata={
                    "chat_id": message.chat.id,
                    "message_id": message.message_id
                }
            )

            # Добавление сообщения в очередь
            await self.queue.push_message(queue_message)

            # Шифрование сообщения для логирования
            encrypted_text = self.security.encrypt_message(message.text or "")
            message_hash = self.security.hash_message(message.text or "")

            # Логирование зашифрованного сообщения
            self.logger.info(
                f"Received message from user {message.from_user.id}. "
                f"Hash: {message_hash}"
            )

            # Проверка прав доступа для административных команд
            if message.text and message.text.split()[0] in ['/admin', '/stats', '/debug']:
                if not self.security.is_admin(message.from_user.id):
                    await message.answer("У вас нет прав для выполнения этой команды.")
                    return

            # Обработка сообщения
            await self.handler.handle_message(message)

        except Exception as e:
            self.logger.error(f"Error processing message: {e}")
            await message.answer("Произошла ошибка при обработке сообщения.")

    async def process_queue(self) -> None:
        """Обработка сообщений из очереди"""
        while True:
            try:
                # Получение сообщения из очереди
                message = await self.queue.get_message()
                if message:
                    self.logger.info(f"Processing queued message: {message.user_id}")
                    # Здесь можно добавить дополнительную обработку
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error processing queue: {e}")
            await asyncio.sleep(1)

    async def start(self):
        """Запуск бота"""
        try:
            # Инициализация компонентов
            await self.queue.connect()
            await self.db.create_tables()

            # Регистрация обработчиков
            self.handler.register_handlers(self.dp)

            # Добавление middleware для обработки сообщений
            self.dp.message.middleware(MessageMiddleware(self))

            # Запуск обработчика очереди
            self.queue_task = asyncio.create_task(self.process_queue())

            # Запуск бота
            self.logger.info("Bot started")
            await self.dp.start_polling(self.bot, allowed_updates=["message", "callback_query"])

        except Exception as e:
            self.logger.error(f"Error starting bot: {e}")
            if self.queue_task:
                self.queue_task.cancel()
                try:
                    await self.queue_task
                except asyncio.CancelledError:
                    pass
        finally:
            await self.cleanup()

    async def cleanup(self):
        """Очистка ресурсов при завершении работы"""
        try:
            if self.queue_task:
                self.queue_task.cancel()
                await self.queue_task
        except asyncio.CancelledError:
            pass

        await self.queue.close()
        await self.bot.session.close()
        await self.storage.close()


def main():
    # Настройка логирования
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    )

    # Создание и запуск бота
    bot = SecureFilamentBot()

    # Запуск бота с обработкой прерываний
    try:
        asyncio.run(bot.start())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot stopped")


if __name__ == "__main__":
    main()