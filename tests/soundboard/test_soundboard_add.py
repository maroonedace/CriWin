from unittest.mock import AsyncMock, Mock, patch

import pytest
from discord import Interaction, User, VoiceState

from src.commands.soundboard.add import handle_add
from src.commands.soundboard.constants import (
    DISPLAY_NAME_INVALID_MESSAGE,
    DUPLICATE_DISPLAY_NAME_MESSAGE,
    INVALID_AUDIO_MESSAGE,
)


class TestSoundboardAdd:
    user_id = 123456789

    @pytest.fixture
    def mock_valid_interaction(self):
        interaction = Mock(spec=Interaction)
        interaction.user = Mock(spec=User)
        interaction.user.id = self.user_id
        interaction.user.voice = Mock(spec=VoiceState)
        interaction.response.defer = AsyncMock()
        return interaction

    @pytest.fixture
    def mock_sound_file(self):
        sound_file = Mock()
        sound_file.filename = "test_sound.mp3"
        sound_file.content_type = "audio/mpeg"
        sound_file.read = AsyncMock(return_value=b"audio-bytes")
        return sound_file

    @pytest.mark.asyncio
    async def test_invalid_sound_name(self, mock_valid_interaction):
        mock_sound_name = "~~~~~~~"
        mock_sound_file = Mock()
        mock_sound_file.filename = "test_sound.mp3"
        mock_sound_file.content_type = "audio/mpeg"

        with patch("src.commands.soundboard.add.get_sounds") as mock_sounds:
            mock_sounds.return_value = [{"name": "Red Flags", "file_name": "test_sound.mp3"}]
            with patch(
                "src.commands.soundboard.add.send_message", new_callable=AsyncMock
            ) as mock_send_message:
                # Add user to active downloads
                await handle_add(mock_valid_interaction, mock_sound_name, mock_sound_file)

                # Assert that send_message was called with correct arguments
                mock_send_message.assert_called_once_with(
                    mock_valid_interaction, DISPLAY_NAME_INVALID_MESSAGE
                )

    @pytest.mark.asyncio
    async def test_invalid_sound_content_type(self, mock_valid_interaction, mock_sound_file):
        mock_sound_name = "RedFlags123"

        mock_sound_file = Mock()
        mock_sound_file.filename = "test_sound.mp4"
        mock_sound_file.content_type = "video/mp4"

        with patch("src.commands.soundboard.add.get_sounds") as mock_sounds:
            mock_sounds.return_value = [{"name": "Red Flags", "file_name": "test_sound.mp3"}]
            with patch(
                "src.commands.soundboard.add.send_message", new_callable=AsyncMock
            ) as mock_send_message:
                # Add user to active downloads
                await handle_add(mock_valid_interaction, mock_sound_name, mock_sound_file)

                # Assert that send_message was called with correct arguments
                mock_send_message.assert_called_once_with(
                    mock_valid_interaction, INVALID_AUDIO_MESSAGE
                )

    @pytest.mark.asyncio
    async def test_duplicate_sound_add(self, mock_valid_interaction, mock_sound_file):
        mock_sound_name = "Red Flags"

        mock_sound_file = Mock()
        mock_sound_file.filename = "test_sound.mp3"
        mock_sound_file.content_type = "audio/mpeg"

        with patch("src.commands.soundboard.add.get_sounds") as mock_sounds:
            mock_sounds.return_value = [{"name": "Red Flags", "file_name": "test_sound.mp3"}]
            with patch(
                "src.commands.soundboard.add.send_message", new_callable=AsyncMock
            ) as mock_send_message:
                # Add user to active downloads
                await handle_add(mock_valid_interaction, mock_sound_name, mock_sound_file)

                # Assert that send_message was called with correct arguments
                mock_send_message.assert_called_once_with(
                    mock_valid_interaction, DUPLICATE_DISPLAY_NAME_MESSAGE
                )

    @pytest.mark.asyncio
    async def test_invalid_sound_add(self, mock_valid_interaction, mock_sound_file):
        mock_sound_name = "RedFlags123"

        mock_sound_file = Mock()
        mock_sound_file.filename = "test_sound.mp3"
        mock_sound_file.content_type = "audio/mpeg"
        mock_sound_file.read = AsyncMock(return_value=b"audio-bytes")

        with patch("src.commands.soundboard.add.get_sounds") as mock_sounds:
            mock_sounds.return_value = [{"name": "Red Flags", "file_name": "test_sound.mp3"}]
            with patch("src.commands.soundboard.add.upload_sound_file") as mock_upload_sound_file:
                mock_upload_sound_file.side_effect = ValueError("Could not upload sound file.")
                with patch(
                    "src.commands.soundboard.add.send_message", new_callable=AsyncMock
                ) as mock_send_message:
                    # Add user to active downloads
                    await handle_add(mock_valid_interaction, mock_sound_name, mock_sound_file)

                    # Assert that send_message was called with correct arguments
                    mock_send_message.assert_called_once_with(
                        mock_valid_interaction, "Could not upload sound file."
                    )

    @pytest.mark.asyncio
    async def test_valid_sound_add(self, mock_valid_interaction, mock_sound_file):
        mock_sound_name = "RedFlags123"

        mock_sound_file = Mock()
        mock_sound_file.filename = "test_sound.mp3"
        mock_sound_file.content_type = "audio/mpeg"
        mock_sound_file.read = AsyncMock(return_value=b"audio-bytes")

        with patch("src.commands.soundboard.add.get_sounds") as mock_sounds:
            mock_sounds.return_value = [{"name": "Red Flags", "file_name": "test_sound.mp3"}]
            with patch("src.commands.soundboard.add.upload_sound_file"):
                with patch(
                    "src.commands.soundboard.add.send_message", new_callable=AsyncMock
                ) as mock_send_message:
                    # Add user to active downloads
                    await handle_add(mock_valid_interaction, mock_sound_name, mock_sound_file)

                    # Assert that send_message was called with correct arguments
                    mock_send_message.assert_called_once_with(
                        mock_valid_interaction,
                        f"✅ Added **{mock_sound_name}** → {mock_sound_file.filename}",
                    )
