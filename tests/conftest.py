import pytest

from bot.config import Config
from tests.fakes.discord import FakeInteraction


@pytest.fixture
def valid_config(monkeypatch):
    """Patch Config with a complete, valid development configuration."""
    monkeypatch.setattr(Config, "ENVIRONMENT", "development")
    monkeypatch.setattr(Config, "DISCORD_TOKEN", "token")
    monkeypatch.setattr(Config, "DEV_GUILD_ID", "123456789")
    monkeypatch.setattr(Config, "MAX_POST_MB", 50)
    monkeypatch.setattr(Config, "COOKIE_DIR", "/nonexistent/criwin/cookies")


@pytest.fixture
def interaction() -> FakeInteraction:
    """A fresh interaction, unanswered, in a direct message."""
    return FakeInteraction()
