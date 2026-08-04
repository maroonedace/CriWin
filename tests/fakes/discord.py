"""Stand-ins for the discord.py objects a command handler touches.

The signatures deliberately match discord.py: defer is keyword-only, send takes
content positionally, and both refuse calls the real API would refuse. A fake
that accepts more than the real thing gives false confidence, which is worse
than no test at all.
"""

from dataclasses import dataclass, field


@dataclass
class SentMessage:
    """One follow-up message, as recorded by FakeFollowup."""

    content: str | None
    ephemeral: bool
    files: list = field(default_factory=list)


class FakeCommandTree:
    """Stands in for discord.app_commands.CommandTree, recording what was called.

    Every method is keyword-only, matching the real signatures, so a call that
    would fail against discord.py fails here too. Registering the same name
    twice raises, as the real tree does with CommandAlreadyRegistered.

    Stricter than discord.py in one respect, deliberately: name and description
    have no defaults, so every command must carry the description users see in
    the Discord command picker.
    """

    def __init__(self):
        self.copied_to = []
        self.synced_to = []
        self.commands = {}

    def command(self, *, name, description):
        def decorator(func):
            if name in self.commands:
                raise ValueError(f"Command {name!r} is already registered")

            self.commands[name] = func

            return func

        return decorator

    def copy_global_to(self, *, guild):
        self.copied_to.append(guild)

    async def sync(self, *, guild=None):
        self.synced_to.append(guild)


class FakeResponse:
    """The interaction's initial response slot, which may be used exactly once."""

    def __init__(self):
        self.deferred_ephemeral: bool | None = None

    async def defer(self, *, ephemeral: bool = False, thinking: bool = False):
        if self.is_done():
            raise RuntimeError("This interaction has already been responded to")

        self.deferred_ephemeral = ephemeral

    def is_done(self) -> bool:
        return self.deferred_ephemeral is not None


class FakeFollowup:
    """Follow-up messages, which Discord rejects until the interaction is answered."""

    def __init__(self, response: FakeResponse):
        self._response = response
        self.messages: list[SentMessage] = []

    async def send(self, content=None, *, ephemeral: bool = False, files=None):
        if not self._response.is_done():
            raise RuntimeError("Cannot send a follow-up before responding")

        self.messages.append(
            SentMessage(content=content, ephemeral=ephemeral, files=files or [])
        )


class FakeUser:
    def __init__(self, user_id: int = 1):
        self.id = user_id


class FakeGuild:
    """A guild with an attachment ceiling, which ticket 5 reads to size delivery."""

    def __init__(self, filesize_limit: int = 10 * 1024 * 1024):
        self.filesize_limit = filesize_limit


class FakeInteraction:
    """Enough of discord.Interaction for a command handler, and no more.

    guild defaults to None because that is what a direct message produces, and
    reading .filesize_limit off it is a real crash rather than a hypothetical.
    """

    def __init__(self, user_id: int = 1, guild: FakeGuild | None = None):
        self.response = FakeResponse()
        self.followup = FakeFollowup(self.response)
        self.user = FakeUser(user_id)
        self.guild = guild

    @property
    def sent(self) -> list[SentMessage]:
        return self.followup.messages
