import logging
import os

import pytest

from bot.config import Config, validate_config
from bot.constants import (
    CONFIG_VALIDATED,
    INVALID_ENVIRONMENT,
    INVALID_MAX_POST_MB,
    MISSING_DEV_GUILD_ID,
    MISSING_TOKEN,
    NON_NUMERIC_DEV_GUILD_ID,
)
from bot.parsing import positive_int


@pytest.mark.usefixtures("valid_config")
class TestValidateConfig:
    def test_development_returns_token(self, caplog):
        caplog.set_level(logging.INFO)

        assert validate_config() == "token"
        assert [record.msg for record in caplog.records] == [CONFIG_VALIDATED]

    def test_production_does_not_require_guild_id(self, monkeypatch, caplog):
        caplog.set_level(logging.INFO)
        monkeypatch.setattr(Config, "ENVIRONMENT", "production")
        monkeypatch.setattr(Config, "DEV_GUILD_ID", None)

        assert validate_config() == "token"
        assert [record.msg for record in caplog.records] == [CONFIG_VALIDATED]
        assert "production" in caplog.text

    @pytest.mark.parametrize("token", [None, ""])
    def test_missing_token_exits(self, monkeypatch, caplog, token):
        monkeypatch.setattr(Config, "DISCORD_TOKEN", token)

        with pytest.raises(SystemExit) as excinfo:
            validate_config()

        assert excinfo.value.code == 1
        assert [record.msg for record in caplog.records] == [MISSING_TOKEN]

    @pytest.mark.parametrize("environment", [None, "", "staging"])
    def test_unknown_environment_exits(self, monkeypatch, caplog, environment):
        monkeypatch.setattr(Config, "ENVIRONMENT", environment)

        with pytest.raises(SystemExit) as excinfo:
            validate_config()

        assert excinfo.value.code == 1
        assert [record.msg for record in caplog.records] == [INVALID_ENVIRONMENT]
        assert repr(environment) in caplog.text

    @pytest.mark.parametrize("guild_id", [None, ""])
    def test_development_without_guild_id_exits(self, monkeypatch, caplog, guild_id):
        monkeypatch.setattr(Config, "DEV_GUILD_ID", guild_id)

        with pytest.raises(SystemExit) as excinfo:
            validate_config()

        assert excinfo.value.code == 1
        assert [record.msg for record in caplog.records] == [MISSING_DEV_GUILD_ID]

    def test_development_with_non_numeric_guild_id_exits(self, monkeypatch, caplog):
        monkeypatch.setattr(Config, "DEV_GUILD_ID", "not-a-number")

        with pytest.raises(SystemExit) as excinfo:
            validate_config()

        assert excinfo.value.code == 1
        assert [record.msg for record in caplog.records] == [NON_NUMERIC_DEV_GUILD_ID]
        assert "'not-a-number'" in caplog.text

    def test_an_unusable_max_post_mb_exits(self, monkeypatch, caplog):
        """positive_int has already turned the bad value into None by now, so
        this is the only place an operator finds out why."""
        monkeypatch.setattr(Config, "MAX_POST_MB", None)

        with pytest.raises(SystemExit) as excinfo:
            validate_config()

        assert excinfo.value.code == 1
        assert [record.msg for record in caplog.records] == [INVALID_MAX_POST_MB]


class TestMaxPostMb:
    @pytest.mark.parametrize(
        "raw, expected",
        [("50", 50), ("1", 1), (" 25 ", 25), ("abc", None), ("0", None), ("-5", None)],
    )
    def test_is_parsed_from_the_environment_without_raising(
        self, monkeypatch, raw, expected
    ):
        """Importing bot.config must never blow up on a typo in .env."""
        monkeypatch.setenv("MAX_POST_MB", raw)

        assert positive_int(os.getenv("MAX_POST_MB")) == expected
