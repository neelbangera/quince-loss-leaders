from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from email.message import Message
from html.parser import HTMLParser
import hashlib
import json
import re
from pathlib import Path
import time
from typing import Iterable
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urldefrag, urlsplit, urlunsplit
from urllib.request import Request, urlopen
import urllib.robotparser
import xml.etree.ElementTree as ET

from .models import ProductObservation, canonicalize_url
from .parser import parse_html
from .storage import Repository


ASSET_EXTENSIONS = {
    ".7z", ".avi", ".bmp", ".css", ".csv", ".doc", ".gif", ".ico", ".jpeg",
    ".jpg", ".js", ".json", ".m4a", ".mov", ".mp3", ".mp4", ".pdf", ".png",
    ".svg", ".tar", ".tgz", ".txt", ".webm", ".webp", ".woff", ".woff2", ".xml",
    ".xls", ".xlsx", ".zip",
}


class CrawlBlocked(Exception):
    def __init__(self, url: str, reason: str) -> None:
        super().__init__(f"{url}: {reason}")
        self.url = url
        self.reason = reason


class CrawlFailed(Exception):
    def __init__(self, url: str, reason: str) -> None:
        super().__init__(f"{url}: {reason}")
        self.url = url
        self.reason = reason


@dataclass(frozen=True)
class CrawlConfig:
    seed_urls: tuple[str, ...]
    allowed_hosts: tuple[str, ...]
    snapshot_dir: Path
    sitemap_urls: tuple[str, ...] = ()
    authorized: bool = False
    max_pages: int = 100
    max_depth: int = 2
    delay_seconds: float = 1.0
    timeout_seconds: float = 20.0
    max_response_bytes: int = 8_000_000
    user_agent: str = "QuinceLossLeaderResearch/0.1 (+authorized crawler)"
    respect_robots: bool = True
    url_pattern: str | None = None

    def __post_init__(self) -> None:
        if not self.authorized:
            raise ValueError(
                "The crawler requires an explicit authorized=True configuration."
            )
        if not self.seed_urls and not self.sitemap_urls:
            raise ValueError("At least one seed URL or sitemap URL is required.")
        if not self.allowed_hosts:
            raise ValueError("At least one allowed host is required.")
        if self.max_pages < 1:
            raise ValueError("max_pages must be positive.")
        if self.max_depth < 0:
            raise ValueError("max_depth cannot be negative.")
        if self.delay_seconds < 0:
            raise ValueError("delay_seconds cannot be negative.")


@dataclass(frozen=True)
class FetchResult:
    requested_url: str
    final_url: str
    status: int
    content_type: str
    body: bytes
    headers: Message


@dataclass
class CrawlResult:
    attempted: int = 0
    fetched: int = 0
    snapshots_saved: int = 0
    product_pages_saved: int = 0
    observations_saved: int = 0
    skipped: int = 0
    blocked: list[dict[str, str]] = field(default_factory=list)
    errors: list[dict[str, str]] = field(default_factory=list)


def normalize_crawl_url(value: str, base_url: str | None = None) -> str | None:
    absolute = urljoin(base_url or "", value)
    absolute, _fragment = urldefrag(absolute)
    parsed = urlsplit(absolute)
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.hostname:
        return None
    normalized = canonicalize_url(absolute)
    if not normalized:
        return None
    return normalized


def is_html_link(url: str) -> bool:
    path = urlsplit(url).path.lower()
    return not any(path.endswith(extension) for extension in ASSET_EXTENSIONS)


def host_for_url(url: str) -> str:
    return (urlsplit(url).hostname or "").lower()


class _LinkCollector(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.hrefs: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "a":
            return
        attributes = {key.lower(): value or "" for key, value in attrs}
        href = attributes.get("href")
        if href:
            self.hrefs.append(href)


def extract_links(html: str, page_url: str, allowed_hosts: Iterable[str]) -> list[str]:
    collector = _LinkCollector()
    collector.feed(html)
    allowed = {host.lower() for host in allowed_hosts}
    links: list[str] = []
    seen: set[str] = set()
    for href in collector.hrefs:
        url = normalize_crawl_url(href, page_url)
        if not url or not is_html_link(url) or host_for_url(url) not in allowed or url in seen:
            continue
        seen.add(url)
        links.append(url)
    return links


class RobotsPolicy:
    """Loads robots rules once per origin and fails closed on fetch errors."""

    def __init__(self, user_agent: str, timeout_seconds: float) -> None:
        self.user_agent = user_agent
        self.timeout_seconds = timeout_seconds
        self._parsers: dict[str, urllib.robotparser.RobotFileParser | None] = {}

    def _origin(self, url: str) -> str:
        parsed = urlsplit(url)
        return urlunsplit((parsed.scheme, parsed.netloc, "", "", ""))

    def _load(self, url: str) -> urllib.robotparser.RobotFileParser | None:
        origin = self._origin(url)
        if origin in self._parsers:
            return self._parsers[origin]

        robots_url = f"{origin}/robots.txt"
        request = Request(robots_url, headers={"User-Agent": self.user_agent})
        parser = urllib.robotparser.RobotFileParser(robots_url)
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                status = getattr(response, "status", 200)
                body = response.read(512_000)
            if status == 404:
                parser.parse(["User-agent: *", "Allow: /"])
            elif status < 200 or status >= 300:
                self._parsers[origin] = None
                return None
            else:
                parser.parse(body.decode("utf-8", errors="replace").splitlines())
        except HTTPError as error:
            if error.code == 404:
                parser.parse(["User-agent: *", "Allow: /"])
            else:
                self._parsers[origin] = None
                return None
        except (OSError, URLError):
            self._parsers[origin] = None
            return None

        self._parsers[origin] = parser
        return parser

    def can_fetch(self, url: str) -> bool:
        parser = self._load(url)
        return parser is not None and parser.can_fetch(self.user_agent, url)


class PoliteFetcher:
    def __init__(self, config: CrawlConfig) -> None:
        self.config = config
        self.allowed_hosts = {host.lower() for host in config.allowed_hosts}
        self.robots = RobotsPolicy(config.user_agent, config.timeout_seconds)
        self._last_request_at: float | None = None

    def _validate_url(self, url: str) -> None:
        if host_for_url(url) not in self.allowed_hosts:
            raise CrawlBlocked(url, "host is not allowlisted")
        if self.config.respect_robots and not self.robots.can_fetch(url):
            raise CrawlBlocked(url, "robots.txt disallows the request or could not be read")

    def _wait(self) -> None:
        if self._last_request_at is None:
            return
        remaining = self.config.delay_seconds - (time.monotonic() - self._last_request_at)
        if remaining > 0:
            time.sleep(remaining)

    def fetch(self, url: str) -> FetchResult:
        self._validate_url(url)
        self._wait()
        request = Request(
            url,
            headers={
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9",
                "User-Agent": self.config.user_agent,
            },
        )
        self._last_request_at = time.monotonic()
        try:
            with urlopen(request, timeout=self.config.timeout_seconds) as response:
                status = int(getattr(response, "status", 200))
                final_url = normalize_crawl_url(response.geturl())
                if not final_url or host_for_url(final_url) not in self.allowed_hosts:
                    raise CrawlBlocked(url, "redirected to a non-allowlisted host")
                body = response.read(self.config.max_response_bytes + 1)
                headers = response.headers
                content_type = headers.get_content_type().lower()
        except CrawlBlocked:
            raise
        except HTTPError as error:
            if error.code in {401, 403, 429, 503}:
                raise CrawlBlocked(url, f"server returned HTTP {error.code}") from error
            raise CrawlFailed(url, f"server returned HTTP {error.code}") from error
        except (OSError, URLError, TimeoutError) as error:
            raise CrawlFailed(url, str(error)) from error

        if len(body) > self.config.max_response_bytes:
            raise CrawlBlocked(url, "response exceeded max_response_bytes")
        if content_type not in {"text/html", "application/xhtml+xml", "application/xml", "text/xml"}:
            raise CrawlBlocked(url, f"unsupported content type: {content_type}")

        text = body.decode(headers.get_content_charset() or "utf-8", errors="replace").lower()
        challenge_markers = ("captcha", "verify you are human", "access denied")
        if any(marker in text for marker in challenge_markers) and len(body) < 1_000_000:
            raise CrawlBlocked(url, "challenge or access-control page detected")

        return FetchResult(
            requested_url=url,
            final_url=final_url,
            status=status,
            content_type=content_type,
            body=body,
            headers=headers,
        )


class SnapshotStore:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def save(self, url: str, body: bytes, captured_at: datetime) -> Path:
        digest = hashlib.sha256(body).hexdigest()
        path_part = urlsplit(url).path.strip("/") or "root"
        slug = re.sub(r"[^A-Za-z0-9._-]+", "-", path_part).strip("-")[:80] or "page"
        destination = self.root / f"{digest[:16]}-{slug}.html"
        if not destination.exists():
            destination.write_bytes(body)
        metadata_path = destination.with_suffix(".json")
        if not metadata_path.exists():
            metadata_path.write_text(
                json.dumps(
                    {
                        "url": url,
                        "captured_at": captured_at.astimezone(timezone.utc).isoformat(),
                        "sha256": digest,
                    },
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
        return destination


def _decode_body(result: FetchResult) -> str:
    charset = result.headers.get_content_charset() or "utf-8"
    return result.body.decode(charset, errors="replace")


def _sitemap_locations(xml_body: bytes) -> tuple[bool, list[str]]:
    try:
        root = ET.fromstring(xml_body)
    except ET.ParseError:
        return False, []
    is_index = root.tag.lower().endswith("sitemapindex")
    locations = [
        element.text.strip()
        for element in root.iter()
        if element.tag.lower().endswith("loc") and element.text and element.text.strip()
    ]
    return is_index, locations


def _looks_like_product(observation: ProductObservation, *, allow_url_match: bool = False) -> bool:
    if not observation.product_name or observation.selling_price is None:
        return False
    if not observation.cost_lines and observation.reported_total_cost is None:
        return False
    # Product JSON-LD/SKU is preferred. This keeps pages such as About Us,
    # which may contain an illustrative cost block, out of product rankings.
    has_structured_identity = bool(
        observation.sku or observation.metadata.get("jsonld_product_count", 0) > 0
    )
    return has_structured_identity or allow_url_match


class AuthorizedCrawler:
    def __init__(
        self,
        config: CrawlConfig,
        repository: Repository,
        *,
        fetcher: object | None = None,
    ) -> None:
        self.config = config
        self.repository = repository
        self.fetcher = fetcher or PoliteFetcher(config)
        self.snapshots = SnapshotStore(config.snapshot_dir)
        self.url_regex = re.compile(config.url_pattern) if config.url_pattern else None

    def _allowed_and_matching(self, url: str) -> bool:
        if host_for_url(url) not in {host.lower() for host in self.config.allowed_hosts}:
            return False
        return self.url_regex is None or bool(self.url_regex.search(url))

    def run(self) -> CrawlResult:
        result = CrawlResult()
        queue: deque[tuple[str, int, bool]] = deque()
        seen: set[str] = set()

        def enqueue(
            url: str,
            depth: int,
            is_sitemap: bool = False,
            force: bool = False,
        ) -> None:
            normalized = normalize_crawl_url(url)
            if not normalized or normalized in seen:
                return
            if not is_sitemap and not force and not self._allowed_and_matching(normalized):
                return
            seen.add(normalized)
            queue.append((normalized, depth, is_sitemap))

        for seed in self.config.seed_urls:
            enqueue(seed, 0, force=True)
        for sitemap in self.config.sitemap_urls:
            enqueue(sitemap, 0, True)

        while queue and result.attempted < self.config.max_pages:
            url, depth, is_sitemap = queue.popleft()
            result.attempted += 1
            try:
                fetched = self.fetcher.fetch(url)
            except CrawlBlocked as error:
                result.blocked.append({"url": error.url, "reason": error.reason})
                continue
            except CrawlFailed as error:
                result.errors.append({"url": error.url, "reason": error.reason})
                continue

            result.fetched += 1
            captured_at = datetime.now(timezone.utc)

            if is_sitemap or fetched.content_type in {"application/xml", "text/xml"}:
                is_index, locations = _sitemap_locations(fetched.body)
                for location in locations:
                    enqueue(location, depth + 1, is_index)
                continue

            html = _decode_body(fetched)
            snapshot_path = self.snapshots.save(fetched.final_url, fetched.body, captured_at)
            result.snapshots_saved += 1
            observation = parse_html(
                html,
                source_ref=str(snapshot_path.resolve()),
                captured_at=captured_at,
                canonical_url=fetched.final_url,
            )
            observation.raw_sha256 = hashlib.sha256(fetched.body).hexdigest()
            observation.metadata.update({"crawl_depth": depth, "http_status": fetched.status})

            if _looks_like_product(observation, allow_url_match=self.url_regex is not None):
                self.repository.save_observation(observation)
                result.product_pages_saved += 1
                result.observations_saved += 1

            if depth >= self.config.max_depth:
                continue
            for link in extract_links(html, fetched.final_url, self.config.allowed_hosts):
                enqueue(link, depth + 1)

        result.skipped = len(queue)
        return result
