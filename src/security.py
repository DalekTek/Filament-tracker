from typing import Set, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel
import hashlib
import hmac
import os
from cryptography.fernet import Fernet


class UserSession(BaseModel):
    """Модель сессии пользователя"""
    user_id: int
    last_activity: datetime
    is_admin: bool = False


class SecurityManager:
    def __init__(self):
        """Инициализация менеджера безопасности"""
        # Генерация ключа шифрования при первом запуске
        self._encryption_key = os.getenv('ENCRYPTION_KEY') or Fernet.generate_key()
        if isinstance(self._encryption_key, bytes):
            print(f"Encryption key: {self._encryption_key.decode()}")
        self._fernet = Fernet(self._encryption_key)

        # Множество активных сессий
        self._active_sessions: Set[int] = set()
        # Словарь для хранения информации о сессиях
        self._sessions: dict[int, UserSession] = {}
        # Время жизни сессии (30 минут)
        self._session_lifetime = timedelta(minutes=30)
        # Список разрешенных пользователей (администраторов)
        self._admin_users = set(map(int, os.getenv('ADMIN_USERS', '').split(',')))
        # Соль для хеширования
        self._salt = os.getenv('HASH_SALT', os.urandom(16).hex())

    def encrypt_message(self, message: str) -> bytes:
        """
        Шифрование сообщения
        :param message: Исходное сообщение
        :return: Зашифрованное сообщение
        """
        return self._fernet.encrypt(message.encode())

    def decrypt_message(self, encrypted_message: bytes) -> str:
        """
        Расшифровка сообщения
        :param encrypted_message: Зашифрованное сообщение
        :return: Расшифрованное сообщение
        """
        return self._fernet.decrypt(encrypted_message).decode()

    def create_session(self, user_id: int) -> bool:
        """
        Создание сессии пользователя
        :param user_id: ID пользователя
        :return: Успешность создания сессии
        """
        is_admin = user_id in self._admin_users
        session = UserSession(
            user_id=user_id,
            last_activity=datetime.now(),
            is_admin=is_admin
        )
        self._sessions[user_id] = session
        self._active_sessions.add(user_id)
        return True

    def validate_session(self, user_id: int) -> bool:
        """
        Проверка валидности сессии
        :param user_id: ID пользователя
        :return: Валидность сессии
        """
        session = self._sessions.get(user_id)
        if not session:
            return False

        if datetime.now() - session.last_activity > self._session_lifetime:
            self.end_session(user_id)
            return False

        session.last_activity = datetime.now()
        return True

    def end_session(self, user_id: int) -> None:
        """
        Завершение сессии пользователя
        :param user_id: ID пользователя
        """
        self._active_sessions.discard(user_id)
        self._sessions.pop(user_id, None)

    def is_admin(self, user_id: int) -> bool:
        """
        Проверка, является ли пользователь администратором
        :param user_id: ID пользователя
        :return: Является ли администратором
        """
        session = self._sessions.get(user_id)
        return session is not None and session.is_admin

    def hash_message(self, message: str) -> str:
        """
        Хеширование сообщения для проверки целостности
        :param message: Исходное сообщение
        :return: Хеш сообщения
        """
        return hmac.new(
            self._salt.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()

    def verify_message(self, message: str, message_hash: str) -> bool:
        """
        Проверка целостности сообщения
        :param message: Исходное сообщение
        :param message_hash: Хеш для проверки
        :return: Результат проверки
        """
        return hmac.compare_digest(
            self.hash_message(message),
            message_hash
        )