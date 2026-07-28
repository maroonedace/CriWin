from unittest.mock import AsyncMock, MagicMock

import pytest

from src.events import handle_dm_message


@pytest.mark.asyncio
async def test_handle_dm_message_echoes_content():
    message = MagicMock()
    message.content = "hello there"
    message.channel.send = AsyncMock()

    await handle_dm_message(message)

    message.channel.send.assert_awaited_once_with("Received your message: hello there")
