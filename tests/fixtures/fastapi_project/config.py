"""Core configuration and settings for the FastAPI fixture application."""

from __future__ import annotations

import os

from dotenv import load_dotenv
from pydantic import BaseModel, Field

# Load environment configuration from .env file
load_dotenv()


class DatabaseSettings(BaseModel):
    """Database connection and pooling parameters."""
    host: str = Field(default="localhost")
    port: int = Field(default=5432)
    name: str = Field(default="ecommerce_db")
    user: str = Field(default="app_user")
    password: str = Field(default="dev_password_only")
    pool_size: int = Field(default=20)
    max_overflow: int = Field(default=10)
    pool_timeout: int = Field(default=30)

    @property
    def connection_url(self) -> str:
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"


class RedisSettings(BaseModel):
    """Redis caching parameters."""
    url: str = Field(default="redis://localhost:6379/0")
    ttl_seconds: int = Field(default=300)
    max_connections: int = Field(default=50)


class SecuritySettings(BaseModel):
    """Authentication and secret settings."""
    jwt_secret_key: str = Field(default_factory=lambda: os.getenv("JWT_SECRET_KEY", "fallback_secret"))
    jwt_algorithm: str = Field(default="HS256")
    token_expire_minutes: int = Field(default=60)
    vault_addr: str = Field(default="https://vault.internal:8200")
    vault_token: str = Field(default_factory=lambda: os.getenv("VAULT_TOKEN", ""))


class AppSettings(BaseModel):
    """Root application configuration."""
    app_name: str = Field(default="Ecommerce API")
    environment: str = Field(default_factory=lambda: os.getenv("APP_ENV", "production"))
    debug: bool = Field(default=False)
    db: DatabaseSettings = Field(default_factory=DatabaseSettings)
    redis: RedisSettings = Field(default_factory=RedisSettings)
    security: SecuritySettings = Field(default_factory=SecuritySettings)


settings = AppSettings()


def get_secret_from_vault(secret_path: str) -> str:
    """Retrieve runtime secret from HashiCorp Vault secrets manager."""
    try:
        import hvac  # type: ignore
        client = hvac.Client(url=settings.security.vault_addr, token=settings.security.vault_token)
        secret_data = client.secrets.kv.v2.read_secret_version(path=secret_path)
        return secret_data["data"]["data"].get("value", "")
    except Exception:
        # Fall back to environment variable
        return os.getenv("BACKUP_SECRET", "")
