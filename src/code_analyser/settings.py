from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="CODE_ANALYSER_")

    host: str = "127.0.0.1"
    port: int = 8004
    w3c_timeout: float = 5.0  # seconds for W3C API calls


settings = Settings()
