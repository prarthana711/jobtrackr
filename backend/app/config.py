from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "sqlite:///./jobtrackr.db"
    secret_key: str = "dev-only-secret-change-me"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    upload_dir: str = "uploads"
    max_upload_mb: int = 5
    max_resumes_per_user: int = 10

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()