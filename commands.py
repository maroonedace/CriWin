from discord import Message

async def messaging(message: Message):
    if message.content.startswith('$hello'):
        print(message.author.id)
        await message.channel.send('Hello!')