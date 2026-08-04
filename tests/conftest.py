import pytest

from bot.config import Config


@pytest.fixture
def valid_config(monkeypatch):
    """Patch Config with a complete, valid development configuration."""
    monkeypatch.setattr(Config, "ENVIRONMENT", "development")
    monkeypatch.setattr(Config, "DISCORD_TOKEN", "token")
    monkeypatch.setattr(Config, "DEV_GUILD_ID", "123456789")
