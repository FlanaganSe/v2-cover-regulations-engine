"""Application configuration via environment variables."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://postgres:postgres@db/regulation_engine"
    openai_api_key: str = ""
    openai_model: str = "gpt-4.1-mini"
    martin_url: str = "http://martin:3000"


settings = Settings()
