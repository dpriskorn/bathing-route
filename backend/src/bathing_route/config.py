from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(Path(__file__).parent.parent / ".env"),
        extra="ignore",
    )

    qlever_endpoint: str = "https://qlever.cs.uni-freiburg.de/api/wikidata"
    wikimedia_bot_user: str = ""
    wikimedia_bot_pass: str = ""


def get_settings() -> Settings:
    return Settings()
