"""
Application configuration management
"""


from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AnalyzerConfig(BaseModel):
    """Configuration for code analysis tools"""

    # Python analyzers
    ruff_enabled: bool = True
    ruff_config: str | None = None
    mypy_enabled: bool = True
    mypy_config: str | None = None

    # Analysis options
    max_complexity: int = 10
    max_line_length: int = 88
    check_type_hints: bool = True
    check_docstrings: bool = True

    # Execution limits
    execution_timeout: int = 30  # seconds
    memory_limit: str = "128m"  # Docker memory limit
    cpu_limit: str = "0.5"  # Docker CPU limit


class SimilarityConfig(BaseModel):
    """Configuration for similarity detection"""

    enabled: bool = True
    threshold: float = 0.8  # Similarity threshold for flagging
    methods: list[str] = ["ast_similarity", "token_similarity"]

    # AI-generated baseline comparison
    use_ai_baselines: bool = True
    ai_baseline_count: int = 5


class DatabaseConfig(BaseModel):
    """Database configuration"""

    url: str = "sqlite+aiosqlite:///./codelens.db"
    echo: bool = False  # SQL logging
    pool_size: int = 5
    max_overflow: int = 10


class Settings(BaseSettings):
    """Application settings"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )

    # Application
    app_name: str = "CodeLens"
    debug: bool = False
    version: str = "0.1.0"

    # API
    api_prefix: str = "/api/v1"
    host: str = "localhost"
    port: int = 8000

    # Security
    secret_key: str = Field(default="your-secret-key-change-in-production")
    access_token_expire_minutes: int = 30

    # Analysis configuration
    analyzer: AnalyzerConfig = Field(default_factory=AnalyzerConfig)
    similarity: SimilarityConfig = Field(default_factory=SimilarityConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)

    # Docker settings
    docker_enabled: bool = True
    docker_image: str = "python:3.11-slim"

    # File limits
    max_file_size: int = 1024 * 1024  # 1MB
    max_files_per_batch: int = 100


# Global settings instance
settings = Settings()
