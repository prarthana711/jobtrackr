from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "sqlite:///./jobtrackr.db"

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()