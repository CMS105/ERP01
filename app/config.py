from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    DATABASE_URL: str = "postgresql+psycopg://postgres:postgres@localhost:5432/lpg_erp"
    REDIS_URL: str = "redis://localhost:6379/0"
    SECRET_KEY: str = "student-secret-key-hackathon-2026"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 40
    DB_POOL_TIMEOUT: int = 30
    DB_POOL_RECYCLE: int = 1800

    CACHE_DEFAULT_TTL_SECONDS: int = 120
    LOGISTICS_TWO_WHEELER_MAX_CAPACITY: int = 4
    LOGISTICS_SMALL_TRUCK_MAX_CAPACITY: int = 30
    LOGISTICS_HIGH_DENSITY_THRESHOLD: int = 5


settings = Settings()
