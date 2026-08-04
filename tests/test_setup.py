import pytest

from bot.commands import download as download_package
from bot.commands import ping as ping_package
from bot.commands.setup import setup_commands
from tests.fakes.discord import FakeCommandTree

URL = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"


@pytest.fixture
def tree() -> FakeCommandTree:
    tree = FakeCommandTree()
    setup_commands(tree)

    return tree


def test_registers_every_command(tree):
    assert sorted(tree.commands) == ["download", "ping"]


@pytest.mark.asyncio
async def test_ping_command_calls_its_handler(tree, interaction, monkeypatch):
    handled = []

    async def fake_handle_ping(interaction):
        handled.append(interaction)

    monkeypatch.setattr(ping_package, "handle_ping", fake_handle_ping)

    await tree.commands["ping"](interaction)

    assert handled == [interaction]


@pytest.mark.asyncio
async def test_download_command_calls_its_handler(tree, interaction, monkeypatch):
    handled = []

    async def fake_handle_download(interaction, url):
        handled.append((interaction, url))

    monkeypatch.setattr(download_package, "handle_download", fake_handle_download)

    await tree.commands["download"](interaction, URL)

    assert handled == [(interaction, URL)]
