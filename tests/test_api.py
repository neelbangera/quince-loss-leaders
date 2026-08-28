from datetime import datetime, timezone
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from quince_loss_leaders.api import RankingService, build_parser
from quince_loss_leaders.parser import parse_html
from quince_loss_leaders.storage import Repository


FIXTURES = Path(__file__).parents[1] / "fixtures"


class ApiTests(unittest.TestCase):
    def test_product_history_returns_observations_and_analytics(self) -> None:
        html = (FIXTURES / "loss-example.html").read_text(encoding="utf-8")
        with TemporaryDirectory() as temporary_directory:
            database = Path(temporary_directory) / "rankings.sqlite3"
            with Repository(database) as repository:
                first = parse_html(html, "loss.html", captured_at=datetime(2026, 1, 1, tzinfo=timezone.utc))
                second = parse_html(html, "loss.html", captured_at=datetime(2026, 1, 2, tzinfo=timezone.utc))
                second.selling_price = second.selling_price + 10
                second.calculate_metrics()
                repository.save_observation(first)
                repository.save_observation(second)

            service = RankingService(database)
            with patch("quince_loss_leaders.api.Repository", wraps=Repository) as repository_class:
                result = service.get_product({
                    "product_key": [first.product_key or ""],
                    "variant_key": [first.variant_key],
                })
                cached = service.get_product({
                    "product_key": [first.product_key or ""],
                    "variant_key": [first.variant_key],
                })

        self.assertEqual(repository_class.call_count, 1)
        self.assertEqual(result, cached)
        self.assertEqual(result["schemaVersion"], 1)
        self.assertEqual(len(result["history"]), 2)
        self.assertEqual(result["analytics"]["observationCount"], 2)
        self.assertEqual(result["analytics"]["lossObservations"], 1)
        self.assertEqual(result["current"]["sellingPrice"], "39.99")

    def test_rankings_support_view_and_taxonomy_filters(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            database = Path(temporary_directory) / "rankings.sqlite3"
            with Repository(database) as repository:
                for fixture in ("loss-example.html", "positive-example.html"):
                    repository.save_observation(
                        parse_html(
                            (FIXTURES / fixture).read_text(encoding="utf-8"),
                            f"https://www.quince.com/men/{fixture}",
                            canonical_url=f"https://www.quince.com/men/{fixture}",
                            captured_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
                        )
                    )

            service = RankingService(database)
            losses = service.get_rankings({"view": ["losses"], "department": ["men"]})
            profit = service.get_rankings({"view": ["profit"], "category": ["bags"]})

            self.assertEqual(losses["total"], 1)
            self.assertEqual(losses["results"][0]["department"], "men")
            self.assertEqual(profit["total"], 1)
            self.assertEqual(profit["results"][0]["category"], "bags")

            by_price = service.get_rankings({"view": ["all"], "sort": ["price_asc"]})
            by_margin = service.get_rankings({"view": ["all"], "sort": ["margin_desc"]})
            by_cost = service.get_rankings({"view": ["all"], "sort": ["cost_desc"]})
            by_name_desc = service.get_rankings({"view": ["all"], "sort": ["name_desc"]})

            self.assertEqual(by_price["results"][0]["sellingPrice"], "29.99")
            self.assertEqual(by_margin["results"][0]["name"], "Example Carry-All Tote")
            self.assertEqual(by_cost["results"][0]["reportedTotalCost"], "80.90")
            self.assertEqual(by_name_desc["results"][0]["name"], "Example Recycled Tote")

    def test_invalid_query_is_rejected(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            service = RankingService(Path(temporary_directory) / "rankings.sqlite3")
            with self.assertRaises(ValueError):
                service.get_rankings({"view": ["unknown"]})

    def test_health_reports_catalog_state(self) -> None:
        html = (FIXTURES / "loss-example.html").read_text(encoding="utf-8")
        with TemporaryDirectory() as temporary_directory:
            database = Path(temporary_directory) / "rankings.sqlite3"
            with Repository(database) as repository:
                repository.save_observation(
                    parse_html(
                        html,
                        "loss-example.html",
                        captured_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
                    )
                )

            health = RankingService(database).health()

        self.assertTrue(health["ok"])
        self.assertEqual(health["observations"], 1)
        self.assertEqual(health["completeObservations"], 1)
        self.assertEqual(health["rankableVariants"], 1)
        self.assertEqual(health["latestCapturedAt"], "2026-01-01T00:00:00+00:00")

    def test_health_does_not_create_missing_database(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            database = Path(temporary_directory) / "missing.sqlite3"
            health = RankingService(database).health()

            self.assertFalse(health["ok"])
            self.assertIn("does not exist", health["error"])
            self.assertFalse(database.exists())

    def test_api_database_can_be_configured_by_environment(self) -> None:
        with patch.dict(os.environ, {"QUINCE_DATABASE": "data/custom.sqlite3"}):
            args = build_parser().parse_args([])

        self.assertEqual(args.database, Path("data/custom.sqlite3"))

    def test_api_defaults_to_us_catalog(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            args = build_parser().parse_args([])

        self.assertEqual(args.database, Path("data/quince-us.sqlite3"))

    def test_display_name_removes_color_and_flags_large_fee(self) -> None:
        html = """
        <html><head>
          <link rel="canonical" href="https://example.test/men/example-chair">
          <meta property="product:price:amount" content="20.00">
          <script type="application/ld+json">
            {"@type":"Product","name":"Example Chair in Performance Velvet - Kid Girl in Charcoal","sku":"EX-FEE-001"}
          </script>
        </head><body><table>
          <tr><td>Materials</td><td>$1.00</td></tr>
          <tr><td>Freight &amp; Handling</td><td>$20.00</td></tr>
          <tr><td>TOTAL COST</td><td>$21.00</td></tr>
        </table></body></html>
        """
        with TemporaryDirectory() as temporary_directory:
            database = Path(temporary_directory) / "rankings.sqlite3"
            with Repository(database) as repository:
                repository.save_observation(
                    parse_html(
                        html,
                        "example-fee.html",
                        captured_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
                    )
                )

            result = RankingService(database).get_rankings({"view": ["all"]})

        self.assertEqual(result["results"][0]["name"], "Example Chair in Performance Velvet")
        self.assertTrue(result["results"][0]["hasExorbitantFees"])

    def test_rankings_cache_reuses_data_and_invalidates_after_write(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            database = Path(temporary_directory) / "rankings.sqlite3"
            with Repository(database) as repository:
                repository.save_observation(
                    parse_html(
                        (FIXTURES / "loss-example.html").read_text(encoding="utf-8"),
                        "loss-example.html",
                        canonical_url="https://www.quince.com/men/loss-example",
                        captured_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
                    )
                )

            service = RankingService(database)
            with patch("quince_loss_leaders.api.Repository", wraps=Repository) as repository_class:
                first = service.get_rankings({"view": ["all"]})
                second = service.get_rankings({"view": ["all"]})

            self.assertEqual(repository_class.call_count, 1)
            self.assertEqual(first["results"], second["results"])

            with Repository(database) as repository:
                repository.save_observation(
                    parse_html(
                        (FIXTURES / "positive-example.html").read_text(encoding="utf-8"),
                        "positive-example.html",
                        canonical_url="https://www.quince.com/women/positive-example",
                        captured_at=datetime(2026, 1, 2, tzinfo=timezone.utc),
                    )
                )

            with patch("quince_loss_leaders.api.Repository", wraps=Repository) as repository_class:
                refreshed = service.get_rankings({"view": ["all"]})

            self.assertEqual(repository_class.call_count, 1)
            self.assertEqual(refreshed["total"], 2)


if __name__ == "__main__":
    unittest.main()
