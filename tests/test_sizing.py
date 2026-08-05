import asyncio

import httpx
import pytest

from bot.config import Config
from bot.media import sizing
from bot.media.platforms import Platform
from bot.media.sizing import (
    ItemSize,
    PostSize,
    SizeSource,
    SizeVerdict,
    content_range_total,
    decide,
    head_size,
    is_segmented,
    is_trustworthy_approximation,
    range_size,
    resolve_item_size,
    resolve_post_size,
)
from bot.media.types import MediaItem, MediaKind, MediaPost
from bot.units import MEGABYTE

SOURCE_URL = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
ITEM_URL = "https://example.com/x.mp4"

MAX_POST_MB = 50
LIMIT = MAX_POST_MB * MEGABYTE

# The rung below the cap that an estimate has to clear to be trusted.
TRUSTED = int(LIMIT * 0.9)


def item(**overrides) -> MediaItem:
    """One video item. Every test varies a field or two, so the rest default."""
    defaults = {"url": ITEM_URL, "kind": MediaKind.VIDEO, "ext": "mp4"}

    return MediaItem(**(defaults | overrides))


def post(*items: MediaItem) -> MediaPost:
    """A post around the given items. Only the items matter to sizing."""
    return MediaPost(SOURCE_URL, Platform.YOUTUBE, "Banana Farm", items)


def sized(size_bytes: int | None) -> ItemSize:
    """An already-resolved item, for exercising the verdict on its own."""
    return ItemSize(item(), size_bytes, SizeSource.REPORTED)


def responds_with_length(total: int):
    """A handler answering every request with a fixed Content-Length."""

    def handler(request):
        return httpx.Response(200, headers={"Content-Length": str(total)})

    return handler


def forbids_requests(request):
    """A handler for rungs that must resolve without touching the network."""
    raise AssertionError(f"sizing must not request {request.url}")


@pytest.fixture(autouse=True)
def fixed_limit(monkeypatch):
    """Pin the cap so a developer's .env cannot change what the suite asserts.

    bot.config calls load_dotenv() at import, so without this a local
    MAX_POST_MB would silently move every boundary in this file.
    """
    monkeypatch.setattr(Config, "MAX_POST_MB", MAX_POST_MB)


@pytest.fixture
def client_for():
    """Build a real AsyncClient whose transport answers from a handler."""

    def build(handler) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            transport=httpx.MockTransport(handler), follow_redirects=True
        )

    return build


@pytest.fixture
def http(monkeypatch):
    """Route every client built inside sizing through a mock transport.

    Only resolve_post_size needs this, because it is the one function that
    constructs its own client. Everything below it takes one as a parameter.
    """
    real_client = httpx.AsyncClient

    def install(handler):
        def factory(**kwargs):
            kwargs["transport"] = httpx.MockTransport(handler)
            return real_client(**kwargs)

        monkeypatch.setattr(httpx, "AsyncClient", factory)

    return install


class TestDecide:
    """The refusal policy, with no items, no client, and no event loop."""

    def test_everything_known_and_under_the_cap_is_accepted(self):
        assert decide((sized(MEGABYTE), sized(MEGABYTE)), 2 * MEGABYTE, LIMIT) is (
            SizeVerdict.ACCEPTED
        )

    def test_exactly_at_the_cap_is_accepted(self):
        assert decide((sized(LIMIT),), LIMIT, LIMIT) is SizeVerdict.ACCEPTED

    def test_one_byte_over_the_cap_is_refused(self):
        assert decide((sized(LIMIT + 1),), LIMIT + 1, LIMIT) is SizeVerdict.TOO_LARGE

    def test_an_unanswered_item_makes_the_post_unknown(self):
        assert decide((sized(MEGABYTE), sized(None)), MEGABYTE, LIMIT) is (
            SizeVerdict.UNKNOWN
        )

    def test_a_known_lower_bound_over_the_cap_beats_an_unknown_sibling(self):
        """Known sizes alone already exceed the cap, so the refusal is certain
        even though one item never answered. Pins the order of the two checks:
        without this, swapping them reports the vaguer UNKNOWN instead."""
        sizes = (sized(60 * MEGABYTE), sized(None))

        assert decide(sizes, 60 * MEGABYTE, LIMIT) is SizeVerdict.TOO_LARGE


class TestIsSegmented:
    @pytest.mark.parametrize(
        "protocol",
        [
            "m3u8",
            "m3u8_native",
            "m3u8_frag_urls",
            "http_dash_segments",
            "http_dash_segments_generator",
            "ism",
            "f4m",
        ],
    )
    def test_a_fragmented_protocol_is_segmented(self, protocol):
        """The authoritative signal, and the only one that catches a manifest
        served from a path with no telltale suffix."""
        plain_looking = item(url="https://cdn.example.com/hls/12345", ext="mp4")

        assert is_segmented(plain_looking) is False
        assert is_segmented(item(url=plain_looking.url, protocol=protocol)) is True

    @pytest.mark.parametrize("protocol", ["", "https", "http", "ftp"])
    def test_an_unfragmented_protocol_is_not_segmented(self, protocol):
        assert is_segmented(item(protocol=protocol)) is False

    @pytest.mark.parametrize("ext", ["m3u8", "m3u", "mpd"])
    def test_a_manifest_extension_is_segmented(self, ext):
        assert is_segmented(item(ext=ext)) is True

    @pytest.mark.parametrize(
        "url",
        [
            "https://cdn.example.com/v/master.m3u8",
            "https://cdn.example.com/v/master.m3u8?token=abc",
            "https://cdn.example.com/v/manifest.mpd",
            "https://cdn.example.com/v/MASTER.M3U8",
        ],
    )
    def test_a_manifest_url_is_segmented_whatever_the_extension_says(self, url):
        assert is_segmented(item(url=url, ext="mp4")) is True

    @pytest.mark.parametrize(
        "url",
        [
            "https://example.com/x.mp4",
            "https://example.com/photo.jpg",
            "https://example.com/m3u8-highlights/x.mp4",
            "",
        ],
    )
    def test_ordinary_media_is_not_segmented(self, url):
        assert is_segmented(item(url=url)) is False


class TestIsTrustworthyApproximation:
    @pytest.mark.parametrize("approximate", [None, 0])
    def test_no_estimate_is_not_trustworthy(self, approximate):
        assert is_trustworthy_approximation(approximate, LIMIT) is False

    def test_an_estimate_well_under_the_cap_is_trusted(self):
        assert is_trustworthy_approximation(MEGABYTE, LIMIT) is True

    def test_an_estimate_exactly_at_the_threshold_is_trusted(self):
        assert is_trustworthy_approximation(TRUSTED, LIMIT) is True

    def test_an_estimate_near_the_cap_is_not_trusted(self):
        assert is_trustworthy_approximation(TRUSTED + MEGABYTE, LIMIT) is False


class TestContentRangeTotal:
    def test_reads_the_total_after_the_slash(self):
        assert content_range_total("bytes 0-0/12345") == 12345

    @pytest.mark.parametrize(
        "header", [None, "", "bytes 0-0/*", "bytes 0-0/nonsense", "garbage"]
    )
    def test_anything_without_a_usable_total_is_none(self, header):
        assert content_range_total(header) is None


class TestHeadSize:
    @pytest.mark.asyncio
    async def test_reads_content_length(self, client_for):
        def handler(request):
            assert request.method == "HEAD"
            assert request.headers["Accept-Encoding"] == "identity"
            return httpx.Response(200, headers={"Content-Length": "9999"})

        async with client_for(handler) as client:
            assert await head_size(client, ITEM_URL) == 9999

    @pytest.mark.parametrize("status", [404, 405, 500])
    @pytest.mark.asyncio
    async def test_an_error_status_answers_nothing(self, client_for, status):
        async with client_for(lambda request: httpx.Response(status)) as client:
            assert await head_size(client, ITEM_URL) is None

    @pytest.mark.asyncio
    async def test_a_missing_content_length_answers_nothing(self, client_for):
        async with client_for(lambda request: httpx.Response(200)) as client:
            assert await head_size(client, ITEM_URL) is None

    @pytest.mark.asyncio
    async def test_returns_none_on_a_connection_error(self, client_for):
        def handler(request):
            raise httpx.ConnectError("refused")

        async with client_for(handler) as client:
            assert await head_size(client, ITEM_URL) is None


class TestRangeSize:
    @pytest.mark.asyncio
    async def test_reads_the_total_from_content_range(self, client_for):
        def handler(request):
            assert request.headers["Range"] == "bytes=0-0"
            return httpx.Response(
                206, headers={"Content-Range": "bytes 0-0/7777"}, content=b"x"
            )

        async with client_for(handler) as client:
            assert await range_size(client, ITEM_URL) == 7777

    @pytest.mark.asyncio
    async def test_a_partial_response_without_a_total_answers_nothing(self, client_for):
        def handler(request):
            return httpx.Response(
                206, headers={"Content-Range": "bytes 0-0/*"}, content=b"x"
            )

        async with client_for(handler) as client:
            assert await range_size(client, ITEM_URL) is None

    @pytest.mark.asyncio
    async def test_a_server_ignoring_range_still_answers_from_content_length(
        self, client_for
    ):
        """The body is never read, so the whole file never lands in memory."""

        def handler(request):
            return httpx.Response(200, content=b"z" * 8888)

        async with client_for(handler) as client:
            assert await range_size(client, ITEM_URL) == 8888

    @pytest.mark.asyncio
    async def test_an_error_status_answers_nothing(self, client_for):
        async with client_for(lambda request: httpx.Response(416)) as client:
            assert await range_size(client, ITEM_URL) is None

    @pytest.mark.asyncio
    async def test_returns_none_on_a_connection_error(self, client_for):
        def handler(request):
            raise httpx.ReadTimeout("too slow")

        async with client_for(handler) as client:
            assert await range_size(client, ITEM_URL) is None


class TestResolveItemSize:
    """The ladder: which rung answers, and which rungs cost a request."""

    @pytest.mark.asyncio
    async def test_a_manifest_is_refused_before_any_request(self, client_for):
        segmented = item(url="https://cdn.example.com/v/master.m3u8", filesize=1234)

        async with client_for(forbids_requests) as client:
            result = await resolve_item_size(client, segmented, LIMIT)

        assert result.source is SizeSource.SEGMENTED
        assert result.size_bytes is None

    @pytest.mark.asyncio
    async def test_a_reported_filesize_wins_without_a_request(self, client_for):
        reported = item(filesize=3 * MEGABYTE, filesize_approx=9 * MEGABYTE)

        async with client_for(forbids_requests) as client:
            result = await resolve_item_size(client, reported, LIMIT)

        assert result.source is SizeSource.REPORTED
        assert result.size_bytes == 3 * MEGABYTE

    @pytest.mark.asyncio
    async def test_a_filesize_of_zero_is_not_an_answer(self, client_for):
        async with client_for(responds_with_length(2048)) as client:
            result = await resolve_item_size(client, item(filesize=0), LIMIT)

        assert result.source is SizeSource.HEAD
        assert result.size_bytes == 2048

    @pytest.mark.asyncio
    async def test_an_estimate_under_the_threshold_is_taken_without_a_request(
        self, client_for
    ):
        async with client_for(forbids_requests) as client:
            result = await resolve_item_size(
                client, item(filesize_approx=MEGABYTE), LIMIT
            )

        assert result.source is SizeSource.APPROXIMATE
        assert result.size_bytes == MEGABYTE

    @pytest.mark.asyncio
    async def test_an_estimate_near_the_cap_is_verified_over_the_network(
        self, client_for
    ):
        near_the_cap = item(filesize_approx=TRUSTED + MEGABYTE)

        async with client_for(responds_with_length(48 * MEGABYTE)) as client:
            result = await resolve_item_size(client, near_the_cap, LIMIT)

        assert result.source is SizeSource.HEAD
        assert result.size_bytes == 48 * MEGABYTE

    @pytest.mark.asyncio
    async def test_an_item_with_no_url_is_unknown_without_a_request(self, client_for):
        async with client_for(forbids_requests) as client:
            result = await resolve_item_size(client, item(url=""), LIMIT)

        assert result.source is SizeSource.UNKNOWN
        assert result.size_bytes is None

    @pytest.mark.asyncio
    async def test_head_answers_when_yt_dlp_reported_nothing(self, client_for):
        async with client_for(responds_with_length(2048)) as client:
            result = await resolve_item_size(client, item(), LIMIT)

        assert result.source is SizeSource.HEAD
        assert result.size_bytes == 2048

    @pytest.mark.asyncio
    async def test_range_answers_when_head_is_refused(self, client_for):
        def handler(request):
            if request.method == "HEAD":
                return httpx.Response(405)
            return httpx.Response(
                206, headers={"Content-Range": "bytes 0-0/7777"}, content=b"x"
            )

        async with client_for(handler) as client:
            result = await resolve_item_size(client, item(), LIMIT)

        assert result.source is SizeSource.RANGE
        assert result.size_bytes == 7777

    @pytest.mark.asyncio
    async def test_an_item_no_rung_can_answer_is_unknown(self, client_for):
        async with client_for(lambda request: httpx.Response(200)) as client:
            result = await resolve_item_size(client, item(), LIMIT)

        assert result.source is SizeSource.UNKNOWN
        assert result.size_bytes is None


class TestResolvePostSize:
    """Post-level results: the sum, the verdict, and the cap that was applied."""

    @pytest.mark.asyncio
    async def test_a_post_with_no_items_is_refused(self):
        assert await resolve_post_size(post()) == PostSize(
            0, SizeVerdict.EMPTY, LIMIT, ()
        )

    @pytest.mark.asyncio
    async def test_a_post_within_the_cap_is_accepted(self, http):
        http(responds_with_length(2 * MEGABYTE))

        result = await resolve_post_size(post(item()))

        assert result.verdict is SizeVerdict.ACCEPTED
        assert result.total_bytes == 2 * MEGABYTE

    @pytest.mark.asyncio
    async def test_sums_every_item_and_probes_each_one(self, http):
        requested = []

        def handler(request):
            requested.append(str(request.url))
            return responds_with_length(4 * MEGABYTE)(request)

        http(handler)

        result = await resolve_post_size(
            post(*(item(url=f"https://example.com/{n}.jpg") for n in range(10)))
        )

        assert len(requested) == 10
        assert len(result.items) == 10
        assert result.total_bytes == 40 * MEGABYTE
        assert result.verdict is SizeVerdict.ACCEPTED

    @pytest.mark.asyncio
    async def test_the_cap_is_per_post_not_per_item(self, http):
        """Twelve items no one of which is close to the cap, refused at 60 MB."""
        http(responds_with_length(5 * MEGABYTE))

        result = await resolve_post_size(
            post(*(item(url=f"https://example.com/{n}.jpg") for n in range(12)))
        )

        assert result.total_bytes == 60 * MEGABYTE
        assert result.verdict is SizeVerdict.TOO_LARGE

    @pytest.mark.asyncio
    async def test_one_unanswered_item_refuses_the_whole_post(self, http):
        def handler(request):
            if request.url.path == "/1.jpg":
                return httpx.Response(200)
            return responds_with_length(MEGABYTE)(request)

        http(handler)

        result = await resolve_post_size(
            post(*(item(url=f"https://example.com/{n}.jpg") for n in range(3)))
        )

        assert result.verdict is SizeVerdict.UNKNOWN
        assert result.total_bytes == 2 * MEGABYTE

    @pytest.mark.asyncio
    async def test_probes_are_capped_at_the_concurrency_limit(self, monkeypatch):
        """A large gallery must not fan out one request per item.

        In-flight requests are counted inside the transport rather than trusting
        httpx's connection pool, which a mock transport bypasses entirely. The
        limit is pinned to a literal here: asserting against PROBE_CONCURRENCY
        itself would pass no matter how high that constant went.
        """
        monkeypatch.setattr(sizing, "PROBE_CONCURRENCY", 4)

        inflight = 0
        peak = 0

        class CountingTransport(httpx.AsyncBaseTransport):
            async def handle_async_request(self, request):
                nonlocal inflight, peak
                inflight += 1
                peak = max(peak, inflight)
                await asyncio.sleep(0.01)
                inflight -= 1
                return httpx.Response(200, headers={"Content-Length": "1000"})

        real_client = httpx.AsyncClient

        def factory(**kwargs):
            kwargs["transport"] = CountingTransport()
            return real_client(**kwargs)

        monkeypatch.setattr(httpx, "AsyncClient", factory)

        result = await resolve_post_size(
            post(*(item(url=f"https://example.com/{n}.jpg") for n in range(40)))
        )

        assert len(result.items) == 40
        assert peak == 4, "probes should saturate the gate but never exceed it"

    @pytest.mark.asyncio
    async def test_the_cap_comes_from_configuration(self, http, monkeypatch):
        monkeypatch.setattr(Config, "MAX_POST_MB", 10)
        http(responds_with_length(11 * MEGABYTE))

        result = await resolve_post_size(post(item()))

        assert result.limit_bytes == 10 * MEGABYTE
        assert result.verdict is SizeVerdict.TOO_LARGE
