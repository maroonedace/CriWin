import pytest
from unittest.mock import AsyncMock, Mock, patch
from discord import Interaction, User, VoiceState
from src.commands.soundboard.play import handle_play
from src.commands.soundboard.constants import UNAVAILABLE_SOUND_MESSAGE, VOICE_STATE_INVALID_MESSAGE

class TestSoundboard:
    user_id = 123456789

    @pytest.fixture
    def mock_invalid_interaction(self):
        interaction = Mock(spec=Interaction)
        interaction.user = Mock(spec=User)
        interaction.user.id = self.user_id
        interaction.user.voice = Mock(spec=VoiceState)
        interaction.user.voice = None
        interaction.response.defer = AsyncMock()
        return interaction
    
    @pytest.fixture
    def mock_valid_interaction(self):
        interaction = Mock(spec=Interaction)
        interaction.user = Mock(spec=User)
        interaction.user.id = self.user_id
        interaction.user.voice = Mock(spec=VoiceState)
        interaction.response.defer = AsyncMock()
        return interaction

    @pytest.mark.asyncio
    async def test_invalid_voice_state(self, mock_invalid_interaction):
        sound_name = "Sus"
        
        with patch('src.commands.soundboard.play.send_message', new_callable=AsyncMock) as mock_send_message:
            # Add user to active downloads
            await handle_play(mock_invalid_interaction, sound_name)
            
            # Assert that send_message was called with correct arguments
            mock_send_message.assert_called_once_with(
                mock_invalid_interaction, 
                VOICE_STATE_INVALID_MESSAGE
            )
        
    @pytest.mark.asyncio
    async def test_unavailable_sounds(self, mock_valid_interaction):
        sound_name = "Sus"
        with patch('src.commands.soundboard.play.get_sounds') as mock_sounds:
            mock_sounds.side_effect = ValueError("Invalid")
            with patch('src.commands.soundboard.play.send_message', new_callable=AsyncMock) as mock_send_message:
                # Add user to active downloads
                await handle_play(mock_valid_interaction, sound_name)
                
                # Assert that send_message was called with correct arguments
                mock_send_message.assert_called_once_with(
                    mock_valid_interaction, 
                    "Invalid"
                )

    @pytest.mark.asyncio
    async def test_unavailable_sound(self, mock_valid_interaction):
        sound_name = "Sus"
        with patch('src.commands.soundboard.play.get_sounds') as mock_sounds:
            mock_sounds.return_value = []
            with patch('src.commands.soundboard.play.send_message', new_callable=AsyncMock) as mock_send_message:
                # Add user to active downloads
                await handle_play(mock_valid_interaction, sound_name)
                
                # Assert that send_message was called with correct arguments
                mock_send_message.assert_called_once_with(
                    mock_valid_interaction, 
                    UNAVAILABLE_SOUND_MESSAGE
                )
