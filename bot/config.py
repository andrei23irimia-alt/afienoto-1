from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    bot_token: str
    spotify_client_id: str | None = None
    spotify_client_secret: str | None = None
    max_duration_seconds: int = 900
    max_playlist_items: int = 10
    download_dir: str = "downloads"
    db_path: str = "bot_data.db"


settings = Settings()
