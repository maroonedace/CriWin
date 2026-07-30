import pytest

from src.config import Config, validate_config


class TestValidateConfig:
    def test_missing_token_exits(self, monkeypatch):
        monkeypatch.setattr(Config, "DISCORD_TOKEN", None)
        monkeypatch.setattr(Config, "GUILD_ID", "123")
        with pytest.raises(SystemExit):
            validate_config()

    def test_missing_guild_exits(self, monkeypatch):
        monkeypatch.setattr(Config, "DISCORD_TOKEN", "token")
        monkeypatch.setattr(Config, "GUILD_ID", None)
        with pytest.raises(SystemExit):
            validate_config()

    def test_non_integer_guild_exits(self, monkeypatch):
        monkeypatch.setattr(Config, "DISCORD_TOKEN", "token")
        monkeypatch.setattr(Config, "GUILD_ID", "not-an-int")
        with pytest.raises(SystemExit):
            validate_config()

    def test_valid_returns_int_guild_id(self, monkeypatch):
        monkeypatch.setattr(Config, "DISCORD_TOKEN", "token")
        monkeypatch.setattr(Config, "GUILD_ID", "123456789")
        assert validate_config() == 123456789


class TestConfigTypes:
    def test_postgres_port_is_int(self):
        assert isinstance(Config.DB_PORT, int)

    def test_storage_secure_is_bool(self):
        assert isinstance(Config.STORAGE_SECURE, bool)

    def test_environment_defaults_to_production(self):
        # Safe default: unset ENVIRONMENT means production (global, single-copy sync).
        assert Config.ENVIRONMENT == "production"
