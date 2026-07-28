from discord import Message


async def handle_dm_message(message: Message):
    await message.channel.send(f"Received your message: {message.content}")
