from datetime import datetime, timezone
from email.message import Message
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
)
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

