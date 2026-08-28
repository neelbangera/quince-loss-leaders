from datetime import datetime, timezone
from email.message import Message
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from quince_loss_leaders.crawler import (
    AuthorizedCrawler,
    CrawlBlocked,
    CrawlConfig,
    FetchResult,
    RobotsPolicy,
    normalize_crawl_url,
)
from quince_loss_leaders.crawler_cli import build_parser, main
from quince_loss_leaders.storage import Repository


FIXTURES = Path(__file__).parents[1] / "fixtures"


def headers(content_type: str) -> Message:
    result = Message()
    result["Content-Type"] = f"{content_type}; charset=utf-8"
    return result


class FakeFetcher:
    def __init__(self, base_url: str, *, disallow_product: bool = False) -> None:
        self.base_url = base_url
        self.disallow_product = disallow_product
        self.requests: list[str] = []
        self.product_html = (FIXTURES / "loss-example.html").read_bytes()

    def fetch(self, url: str) -> FetchResult:
        self.requests.append(url)
        if url.endswith("/product.html") and self.disallow_product:
            raise CrawlBlocked(url, "robots.txt disallows the request")
        if url.endswith("/sitemap.xml"):
            body = (
                b"<?xml version='1.0'?><urlset xmlns='http://www.sitemaps.org/schemas/sitemap/0.9'>"
                + f"<url><loc>{self.base_url}/product.html</loc></url></urlset>".encode("utf-8")
            )
            return FetchResult(url, url, 200, "application/xml", body, headers("application/xml"))
        if url.endswith("/product.html"):
            return FetchResult(url, url, 200, "text/html", self.product_html, headers("text/html"))
        body = (
            b"<html><body>"
            b"<a href='/product.html'>product</a>"
            b"<a href='https://outside.example/product.html'>outside</a>"
            b"<a href='/image.jpg'>image</a>"
            b"</body></html>"
        )
        return FetchResult(url, url, 200, "text/html", body, headers("text/html"))


class _RobotsResponse:
    status = 200

    def __init__(self, body: bytes) -> None:
        self.body = body

    def read(self, limit: int = -1) -> bytes:
        return self.body[:limit]

    def __enter__(self) -> "_RobotsResponse":
        return self

    def __exit__(self, *args: object) -> None:
        return None


class CrawlerTests(unittest.TestCase):
    def make_config(self, root: Path, base_url: str, **kwargs: object) -> CrawlConfig:
        return CrawlConfig(
            seed_urls=(f"{base_url}/",),
            allowed_hosts=("example.test",),
            snapshot_dir=root / "pages",
            authorized=True,
            max_pages=10,
            max_depth=1,
            delay_seconds=0,
            **kwargs,
        )

    def test_crawls_links_and_persists_product_snapshot(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            base_url = "https://example.test"
            fetcher = FakeFetcher(base_url)
            config = self.make_config(root, base_url)
            with Repository(root / "observations.sqlite3") as repository:
                result = AuthorizedCrawler(config, repository, fetcher=fetcher).run()
                losses = repository.loss_leaders()

            self.assertEqual(result.product_pages_saved, 1)
            self.assertEqual(len(losses), 1)
            self.assertEqual(losses[0].name, "Example Recycled Tote")
            self.assertTrue(list((root / "pages").glob("*.html")))
            self.assertEqual(fetcher.requests, [f"{base_url}/", f"{base_url}/product.html"])

    def test_sitemap_discovers_product_without_html_seed(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            base_url = "https://example.test"
            fetcher = FakeFetcher(base_url)
            config = CrawlConfig(
                seed_urls=(),
                sitemap_urls=(f"{base_url}/sitemap.xml",),
                allowed_hosts=("example.test",),
                snapshot_dir=root / "pages",
                authorized=True,
                max_pages=10,
                delay_seconds=0,
            )
            with Repository(root / "observations.sqlite3") as repository:
                result = AuthorizedCrawler(config, repository, fetcher=fetcher).run()

            self.assertEqual(result.product_pages_saved, 1)
            self.assertEqual(fetcher.requests, [f"{base_url}/sitemap.xml", f"{base_url}/product.html"])

    def test_url_pattern_cannot_promote_a_non_product_page(self) -> None:
        non_product_html = b"""
        <html><head><meta property="product:price:amount" content="20.00"></head>
        <body><h1>About our pricing</h1>
        <table><tr><td>Materials</td><td>$10.00</td></tr>
        <tr><td>TOTAL COST</td><td>$10.00</td></tr></table></body></html>
        """

        class NonProductFetcher:
            def fetch(self, url: str) -> FetchResult:
                return FetchResult(
                    url,
                    url,
                    200,
                    "text/html",
                    non_product_html,
                    headers("text/html"),
                )

        with TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            config = CrawlConfig(
                seed_urls=("https://example.test/about",),
                allowed_hosts=("example.test",),
                snapshot_dir=root / "pages",
                authorized=True,
                max_pages=2,
                max_depth=0,
                delay_seconds=0,
                url_pattern=r"https://example\.test/.*",
            )
            with Repository(root / "observations.sqlite3") as repository:
                result = AuthorizedCrawler(
                    config,
                    repository,
                    fetcher=NonProductFetcher(),
                ).run()
                rankings = repository.rankings()

            self.assertEqual(result.observations_saved, 0)
            self.assertEqual(result.non_product_pages, 1)
            self.assertEqual(rankings, [])

    def test_crawl_reports_parse_status_and_truncation(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            base_url = "https://example.test"
            config = CrawlConfig(
                seed_urls=(f"{base_url}/",),
                allowed_hosts=("example.test",),
                snapshot_dir=root / "pages",
                authorized=True,
                max_pages=1,
                max_depth=1,
                delay_seconds=0,
            )
            with Repository(root / "observations.sqlite3") as repository:
                result = AuthorizedCrawler(
                    config,
                    repository,
                    fetcher=FakeFetcher(base_url),
                ).run()

            self.assertEqual(result.attempted, 1)
            self.assertTrue(result.truncated)
            self.assertEqual(result.skipped, 1)
            self.assertEqual(result.html_pages_fetched, 1)
            self.assertEqual(result.parse_status_counts, {"partial": 1})

    def test_invalid_sitemap_is_reported(self) -> None:
        class InvalidSitemapFetcher:
            def fetch(self, url: str) -> FetchResult:
                return FetchResult(
                    url,
                    url,
                    200,
                    "application/xml",
                    b"<not-valid-sitemap",
                    headers("application/xml"),
                )

        with TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            config = CrawlConfig(
                seed_urls=(),
                sitemap_urls=("https://example.test/sitemap.xml",),
                allowed_hosts=("example.test",),
                snapshot_dir=root / "pages",
                authorized=True,
                max_pages=2,
                delay_seconds=0,
            )
            with Repository(root / "observations.sqlite3") as repository:
                result = AuthorizedCrawler(
                    config,
                    repository,
                    fetcher=InvalidSitemapFetcher(),
                ).run()

            self.assertEqual(result.sitemaps_fetched, 1)
            self.assertEqual(result.errors[0]["reason"], "invalid sitemap XML")
            self.assertFalse(result.truncated)

    def test_robots_disallow_is_recorded_without_bypass(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            base_url = "https://example.test"
            fetcher = FakeFetcher(base_url, disallow_product=True)
            config = self.make_config(root, base_url)
            with Repository(root / "observations.sqlite3") as repository:
                result = AuthorizedCrawler(config, repository, fetcher=fetcher).run()

            self.assertEqual(result.product_pages_saved, 0)
            self.assertEqual(result.blocked[0]["reason"], "robots.txt disallows the request")

    def test_robots_policy_parses_rules(self) -> None:
        response = _RobotsResponse(b"User-agent: *\nDisallow: /private\nAllow: /\n")

        with patch("quince_loss_leaders.crawler.urlopen", return_value=response):
            policy = RobotsPolicy("ResearchBot/1.0", 1.0)
            self.assertTrue(policy.can_fetch("https://example.test/public"))
            self.assertFalse(policy.can_fetch("https://example.test/private/data"))

    def test_authorization_is_required(self) -> None:
        with self.assertRaises(ValueError):
            CrawlConfig(
                seed_urls=("https://example.test/",),
                allowed_hosts=("example.test",),
                snapshot_dir=Path("/tmp/pages"),
            )

    def test_invalid_url_pattern_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            CrawlConfig(
                seed_urls=("https://example.test/",),
                allowed_hosts=("example.test",),
                snapshot_dir=Path("/tmp/pages"),
                authorized=True,
                url_pattern="[",
            )

    def test_crawler_cli_uses_api_database_environment_by_default(self) -> None:
        with patch.dict(os.environ, {"QUINCE_DATABASE": "data/custom.sqlite3"}):
            args = build_parser().parse_args(
                ["--authorized", "--allowed-host", "example.test", "--seed", "https://example.test/"]
            )

        self.assertEqual(args.database, Path("data/custom.sqlite3"))

    def test_crawler_cli_rejects_invalid_rankable_ratio(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            with patch("sys.stderr"):
                result = main(
                    [
                        "--authorized",
                        "--allowed-host",
                        "example.test",
                        "--seed",
                        "https://example.test/",
                        "--min-rankable-ratio",
                        "1.1",
                    ]
                )

        self.assertEqual(result, 2)

    def test_normalizes_spaces_in_sitemap_paths(self) -> None:
        self.assertEqual(
            normalize_crawl_url("https://example.test/girl sleep"),
            "https://example.test/girl%20sleep",
        )
