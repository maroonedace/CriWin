from unittest.mock import AsyncMock, MagicMock

import pytest
from discord import Interaction

from src.core.messaging import send_message


@pytest.mark.asyncio
async def test_send_message():
    mock_interaction = MagicMock(spec=Interaction)
    mock_followup = AsyncMock()
    mock_interaction.followup = mock_followup

    test_message = "Hello, World!"

    await send_message(mock_interaction, test_message)

    mock_followup.send.assert_called_once_with(test_message, ephemeral=True)
