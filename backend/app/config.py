from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "sqlite:///./jobtrackr.db"
    secret_key: str = "dev-only-secret-change-me"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    upload_dir: str = "uploads"
    max_upload_mb: int = 5
    max_resumes_per_user: int = 10

    # Addresses of web pages that are allowed to call this API (comma-separated)
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    # Email. Leave smtp_host empty to print emails to the console instead of sending them.
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    email_from: str = "JobTrackr <noreply@localhost>"

    # Reminders
    reminder_loop_enabled: bool = False  # off by default, so tests and scripts never start it
    reminder_check_seconds: int = 60
    reminder_max_attempts: int = 3
    max_pending_reminders_per_user: int = 50

    model_config = SettingsConfigDict(env_file=".env")

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()