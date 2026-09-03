from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "Ajali Alert API"
    DEBUG: bool = False
    DATABASE_URL: str = "postgresql://ajali:ajali@localhost:5432/ajali"
    SECRET_KEY: str = "dev-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    ALLOWED_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:5173", "http://127.0.0.1:5500"]

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
