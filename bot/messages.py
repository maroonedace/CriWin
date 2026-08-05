"""Text sent to users in Discord.

Separate from bot/constants.py, which holds log templates written for the
operator. These two sets read differently, change for different reasons, and
would otherwise collide on names like EXTRACTION_FAILED.

Templates use str.format with named placeholders, since they are built eagerly
at the call site rather than lazily by the logging module.
"""

UNTITLED_POST = "Untitled"

POST_SUMMARY = "**{title}** — {platform}, {count} item(s)"
UNSUPPORTED_PLATFORM = "That link is not from a supported platform."
EXTRACTION_FAILED = "Could not read that link."

POST_TOO_LARGE = "That post is {size} MB, over the {limit} MB limit."
POST_SIZE_UNKNOWN = "Could not work out how big that post is, so it was not downloaded."
POST_EMPTY = "That link has no downloadable media."
