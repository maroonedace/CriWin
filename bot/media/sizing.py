"""Resolve how big a post is before a single byte of it is fetched."""

import asyncio
import logging
from dataclasses import dataclass
from enum import StrEnum
from urllib.parse import urlparse

import httpx

from bot.config import Config
from bot.constants import POST_SIZE_RESOLVED, SIZE_PROBE_FAILED
from bot.media.types import MediaItem, MediaPost
from bot.units import MEGABYTE
from bot.parsing import positive_int

logger = logging.getLogger(__name__)

# yt-dlp's own names for the transports that deliver a stream as many fragments
# behind a manifest, taken from its PROTOCOL_MAP. This is the authoritative
# signal. The extension and URL checks below are heuristics that only matter
# when an extractor reports no protocol at all.
SEGMENTED_PROTOCOLS = frozenset(
    {
        "m3u8",
        "m3u8_native",
        "m3u8_frag_urls",
        "http_dash_segments",
        "http_dash_segments_generator",
        "ism",
        "f4m",
    }
)

SEGMENTED_EXTENSIONS = frozenset({"m3u", "m3u8", "mpd"})
SEGMENTED_SUFFIXES = (".m3u", ".m3u8", ".mpd")

APPROXIMATE_TRUST_RATIO = 0.9

PROBE_TIMEOUT = httpx.Timeout(10.0, connect=5.0)

# How many items may be probed at once. A gallery can hold dozens, and firing
# all of them at a single CDN from a two-core host is both rude and a burst the
# host does not need. Sequential would be slow enough to notice on a carousel.
PROBE_CONCURRENCY = 8

PROBE_HEADERS = {"Accept-Encoding": "identity"}
RANGE_HEADERS = PROBE_HEADERS | {"Range": "bytes=0-0"}


class SizeSource(StrEnum):
    """Which rung of the ladder produced a size, kept for logs and tests."""

    REPORTED = "reported"
    APPROXIMATE = "approximate"
    HEAD = "head"
    RANGE = "range"
    SEGMENTED = "segmented"
    UNKNOWN = "unknown"


class SizeVerdict(StrEnum):
    ACCEPTED = "accepted"
    TOO_LARGE = "too_large"
    UNKNOWN = "unknown"
    EMPTY = "empty"


@dataclass(frozen=True, slots=True)
class ItemSize:
    """One item's size, and where the number came from."""

    item: MediaItem
    size_bytes: int | None
    source: SizeSource


@dataclass(frozen=True, slots=True)
class PostSize:
    """The whole post's size and the accept or refuse decision.

    total_bytes is a lower bound rather than a true total. Items no rung could
    answer contribute nothing to the sum, so on an UNKNOWN verdict the real post
    is larger by an unknown amount. Only trust it when the verdict is ACCEPTED.
    """

    total_bytes: int
    verdict: SizeVerdict
    limit_bytes: int
    items: tuple[ItemSize, ...]

    @property
    def accepted(self) -> bool:
        return self.verdict is SizeVerdict.ACCEPTED


async def resolve_post_size(post: MediaPost) -> PostSize:
    """Size every item in a post and decide whether the post is allowed."""
    limit = Config.MAX_POST_MB * MEGABYTE

    if not post.items:
        return PostSize(0, SizeVerdict.EMPTY, limit, ())

    async with httpx.AsyncClient(
        timeout=PROBE_TIMEOUT, follow_redirects=True
    ) as client:
        gate = asyncio.Semaphore(PROBE_CONCURRENCY)

        async def resolve_one(item: MediaItem) -> ItemSize:
            async with gate:
                return await resolve_item_size(client, item, limit)

        sizes = tuple(
            await asyncio.gather(*(resolve_one(item) for item in post.items))
        )

    total = sum(size.size_bytes or 0 for size in sizes)
    verdict = decide(sizes, total, limit)

    logger.info(POST_SIZE_RESOLVED, post.source_url, total, verdict)

    return PostSize(total, verdict, limit, sizes)


async def resolve_item_size(
    client: httpx.AsyncClient, item: MediaItem, limit: int
) -> ItemSize:
    """Walk the ladder until a rung answers, cheapest rung first.

    A filesize of zero is treated as no answer. Extractors report it for items
    they know nothing about, and a real media file is never zero bytes.
    """
    if is_segmented(item):
        return ItemSize(item, None, SizeSource.SEGMENTED)

    if item.filesize:
        return ItemSize(item, item.filesize, SizeSource.REPORTED)

    if is_trustworthy_approximation(item.filesize_approx, limit):
        return ItemSize(item, item.filesize_approx, SizeSource.APPROXIMATE)

    if not item.url:
        return ItemSize(item, None, SizeSource.UNKNOWN)

    size = await head_size(client, item.url)
    if size is not None:
        return ItemSize(item, size, SizeSource.HEAD)

    size = await range_size(client, item.url)
    if size is not None:
        return ItemSize(item, size, SizeSource.RANGE)

    return ItemSize(item, None, SizeSource.UNKNOWN)


def decide(sizes: tuple[ItemSize, ...], total: int, limit: int) -> SizeVerdict:
    """Turn per-item sizes into one decision.

    The known sizes are a lower bound on the true total, so a total already over
    the cap is certain even when another item never answered. That case reports
    TOO_LARGE rather than UNKNOWN because it is the more useful of two refusals.
    """
    if total > limit:
        return SizeVerdict.TOO_LARGE

    if any(size.size_bytes is None for size in sizes):
        return SizeVerdict.UNKNOWN

    return SizeVerdict.ACCEPTED


def is_segmented(item: MediaItem) -> bool:
    """Whether the item's URL is a manifest rather than the media itself.

    Three signals, weakest last. The protocol is what yt-dlp actually knows.
    The extension is nearly useless on its own, since yt-dlp reports "mp4" for
    HLS variants, and the URL suffix misses any manifest served from a path
    without one.
    """
    if item.protocol in SEGMENTED_PROTOCOLS:
        return True

    if item.ext in SEGMENTED_EXTENSIONS:
        return True

    return urlparse(item.url).path.lower().endswith(SEGMENTED_SUFFIXES)


def is_trustworthy_approximation(approximate: int | None, limit: int) -> bool:
    """Whether an estimate is far enough under the cap to act on."""
    return bool(approximate) and approximate <= limit * APPROXIMATE_TRUST_RATIO


async def head_size(client: httpx.AsyncClient, url: str) -> int | None:
    """Ask for headers without a body. One round trip, no bytes transferred."""
    try:
        response = await client.head(url, headers=PROBE_HEADERS)
    except httpx.HTTPError:
        logger.warning(SIZE_PROBE_FAILED, "HEAD", url)
        return None

    if response.is_error:
        return None

    return positive_int(response.headers.get("Content-Length"))


async def range_size(client: httpx.AsyncClient, url: str) -> int | None:
    """Ask for one byte, for servers that refuse HEAD.

    The response is streamed and abandoned unread, so a server that ignores the
    Range header and starts sending the whole file never lands in memory. That
    case still answers, since its Content-Length is the full size.
    """
    try:
        async with client.stream("GET", url, headers=RANGE_HEADERS) as response:
            if response.status_code == httpx.codes.PARTIAL_CONTENT:
                return content_range_total(response.headers.get("Content-Range"))

            if response.is_error:
                return None

            return positive_int(response.headers.get("Content-Length"))
    except httpx.HTTPError:
        logger.warning(SIZE_PROBE_FAILED, "GET", url)
        return None


def content_range_total(header: str | None) -> int | None:
    """Read the total out of "bytes 0-0/12345".

    A server that knows the range but not the length writes "*" for the total.
    """
    if not header or "/" not in header:
        return None

    return positive_int(header.rpartition("/")[2])
