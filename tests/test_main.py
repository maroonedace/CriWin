import pytest

import bot.__main__ as entrypoint


class FakeBot:
    def __init__(self, calls):
        self.calls = calls

    def run(self, token):
        self.calls.append(("run", token))


def test_main_validates_before_running(monkeypatch):
    calls = []

    def fake_validate_config():
        calls.append("validate")
        return "token"

    def fake_discord_bot():
        return FakeBot(calls)

    monkeypatch.setattr(entrypoint, "validate_config", fake_validate_config)
    monkeypatch.setattr(entrypoint, "DiscordBot", fake_discord_bot)

    entrypoint.main()

    assert calls == ["validate", ("run", "token")]


def test_main_does_not_start_the_bot_when_validation_fails(monkeypatch):
    calls = []

    def exiting_validate_config():
        raise SystemExit(1)

    def fake_discord_bot():
        calls.append("construct")
        return FakeBot(calls)

    monkeypatch.setattr(entrypoint, "validate_config", exiting_validate_config)
    monkeypatch.setattr(entrypoint, "DiscordBot", fake_discord_bot)

    with pytest.raises(SystemExit):
        entrypoint.main()

    assert calls == []
