from dataclasses import dataclass
from typing import List
from environs import Env

@dataclass
class DatabaseConfig:
    path: str

@dataclass
class RedisConfig:
    host: str
    port: int
    password: str = None

@dataclass
class SecurityConfig:
    encryption_key: str
    admin_users: List[int]
    hash_salt: str
    session_lifetime: int = 30  # minutes

@dataclass
class Config:
    bot_token: str
    database: DatabaseConfig
    redis: RedisConfig
    security: SecurityConfig

def load_config() -> Config:
    """Загрузка конфигурации из переменных окружения"""
    env = Env()
    env.read_env()

    return Config(
        bot_token=env.str("BOT_TOKEN"),
        database=DatabaseConfig(
            path=env.str("DATABASE_PATH", "filament.db")
        ),
        redis=RedisConfig(
            host=env.str("REDIS_HOST", "localhost"),
            port=env.int("REDIS_PORT", 6379),
            password=env.str("REDIS_PASSWORD", None)
        ),
        security=SecurityConfig(
            encryption_key=env.str("ENCRYPTION_KEY", None),
            admin_users=list(map(int, env.list("ADMIN_USERS", []))),
            hash_salt=env.str("HASH_SALT", None),
            session_lifetime=env.int("SESSION_LIFETIME", 30)
        )
    )