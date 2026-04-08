from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str = "postgres://user:pass@localhost:5432/salpyeobom"
    SECRET_KEY: str = "change-me-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 720  # 12 hours

    # 쉼표로 구분된 허용 Origin 목록
    # 예) CORS_ORIGINS=https://example.com,https://admin.example.com
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:5173,http://localhost:5500"


settings = Settings()
