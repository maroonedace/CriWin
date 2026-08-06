"""Find the cookie file yt-dlp should authenticate a platform with.

Cookies live in a directory bind-mounted read-only into the container, one
Netscape-format file per platform, named after the platform. Nothing here
writes: rotation is `make load-cookies` on the host, which is the payoff of
storing cookies on disk rather than in the database.
"""

import logging
import os
from pathlib import Path

from bot.config import Config
from bot.constants import COOKIE_UNREADABLE
from bot.media.platforms import Platform

logger = logging.getLogger(__name__)


def cookie_file(platform: Platform) -> str | None:
    """The cookie file for a platform, or None when there is not a usable one.

    A missing file, and a missing directory, are both ordinary: a fresh install
    has no cookies and the platforms that do not need them never will. Neither
    raises.
    """
    path = Path(Config.COOKIE_DIR) / f"{platform}.txt"

    if not path.is_file():
        return None

    # A cookie the process cannot open is a misconfiguration rather than an
    # absence, and it is worth saying so. Returning None keeps extraction on the
    # same path as having no cookie at all.
    #
    # This never fires in the container as things stand, because the image sets
    # no USER and root bypasses permission checks. It is a development guard
    # until that changes, not a production one.
    if not os.access(path, os.R_OK):
        logger.warning(COOKIE_UNREADABLE, path)
        return None

    return str(path)
