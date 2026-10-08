from dataclasses import replace
from datetime import datetime, timezone
from decimal import Decimal
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
        self.assertEqual(result["current"]["costLines"][0]["label"], "Materials")
        self.assertEqual(result["current"]["costLines"][0]["amount"], "10.00")

    def test_rankings_expose_latest_capture_not_build_time(self) -> None:
        html = (FIXTURES / "loss-example.html").read_text(encoding="utf-8")
        source = "https://www.quince.com/men/loss-example.html"
        with TemporaryDirectory() as temporary_directory:
            database = Path(temporary_directory) / "rankings.sqlite3"
            with Repository(database) as repository:
                for captured_at in (
                    datetime(2026, 1, 1, tzinfo=timezone.utc),
                    datetime(2026, 1, 5, tzinfo=timezone.utc),
                ):
                    repository.save_observation(
                        parse_html(html, source, canonical_url=source, captured_at=captured_at)
                    )

            result = RankingService(database).get_rankings({"view": ["all"]})

        self.assertEqual(len(result["results"]), 1)
        self.assertEqual(result["latestCapturedAt"], result["results"][0]["capturedAt"])
        self.assertTrue(result["latestCapturedAt"].startswith("2026-01-05"))
        self.assertNotEqual(result["latestCapturedAt"], result["generatedAt"])

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
            loss_facets = service.get_rankings({"view": ["losses"]})
            profit_facets = service.get_rankings({"view": ["profit"]})

            self.assertEqual(losses["total"], 1)
            self.assertEqual(losses["results"][0]["department"], "men")
            self.assertEqual(profit["total"], 1)
            self.assertEqual(profit["results"][0]["category"], "bags")
            self.assertEqual(
                {facet["value"]: facet["count"] for facet in loss_facets["facets"]["departments"]},
                {"men": 1},
            )
            self.assertEqual(
                {facet["value"]: facet["count"] for facet in loss_facets["facets"]["categories"]},
                {"bags": 1},
            )
            self.assertEqual(
                {facet["value"]: facet["count"] for facet in profit_facets["facets"]["departments"]},
                {"men": 1},
            )
            self.assertEqual(
                {facet["value"]: facet["count"] for facet in profit_facets["facets"]["categories"]},
                {"bags": 1},
            )

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
          <meta property="og:image" content="https://cdn.example.test/example-chair.jpg">
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
        self.assertEqual(
            result["results"][0]["imageUrl"],
            "https://cdn.example.test/example-chair.jpg",
        )

    def test_normalized_duties_are_excluded_from_rankings_and_flagged(self) -> None:
        html = """
        <html><head>
          <link rel="canonical" href="https://example.test/home/fee-check">
          <meta property="product:price:amount" content="100.00">
          <script type="application/ld+json">
            {"@type":"Product","name":"Fee Check Product","sku":"EX-DUTY-001"}
          </script>
        </head><body><table>
          <tr><td>Materials</td><td>$12.00</td></tr>
          <tr><td>Crafting Cost</td><td>$8.00</td></tr>
          <tr><td>Duties, Taxes, And Fees</td><td>$21.00</td></tr>
          <tr><td>TOTAL COST</td><td>$41.00</td></tr>
        </table></body></html>
        """
        with TemporaryDirectory() as temporary_directory:
            database = Path(temporary_directory) / "rankings.sqlite3"
            with Repository(database) as repository:
                repository.save_observation(parse_html(html, "fee-check.html"))

            result = RankingService(database).get_rankings({"view": ["all"]})

        self.assertEqual(result["results"][0]["reportedTotalCost"], "20.00")
        self.assertEqual(result["results"][0]["unitSpread"], "80.00")
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

    def test_same_price_variants_are_grouped_without_losing_variant_metrics(self) -> None:
        html = (FIXTURES / "positive-example.html").read_text(encoding="utf-8")
        with TemporaryDirectory() as temporary_directory:
            database = Path(temporary_directory) / "rankings.sqlite3"
            with Repository(database) as repository:
                oak = parse_html(html, "july-oak.html")
                oak.product_key = "sku:LB85682"
                oak.variant_key = "70343"
                oak.product_name = "July Haze in Oak"
                oak.canonical_url = "https://www.quince.com/home/july-haze"
                oak.metadata.update({
                    "parent_product_id": "5977",
                    "variant_label": '21.25"x26.25" / Oak',
                    "variant_color": "Oak",
                    "variant_size": '21.25"x26.25"',
                })

                maple = parse_html(html, "july-maple.html")
                maple.product_key = "sku:LB85683"
                maple.variant_key = "70344"
                maple.product_name = "July Haze in Maple"
                maple.canonical_url = "https://www.quince.com/home/july-haze"
                maple.reported_total_cost = Decimal("82.00")
                maple.cost_lines[0] = replace(
                    maple.cost_lines[0],
                    amount=maple.cost_lines[0].amount + Decimal("1.10"),
                )
                maple.calculate_metrics()
                maple.metadata.update({
                    "parent_product_id": "5977",
                    "variant_label": '21.25"x26.25" / Maple',
                    "variant_color": "Maple",
                    "variant_size": '21.25"x26.25"',
                })

                repository.save_observation(oak)
                repository.save_observation(maple)

            result = RankingService(database).get_rankings({"view": ["all"]})

        self.assertEqual(result["total"], 1)
        grouped = result["results"][0]
        self.assertEqual(grouped["variantCount"], 2)
        self.assertEqual(grouped["variantColors"], ["Maple", "Oak"])
        self.assertTrue(grouped["metricsMixed"])
        self.assertEqual(grouped["reportedTotalCostMin"], "80.90")
        self.assertEqual(grouped["reportedTotalCostMax"], "82.00")
        self.assertEqual(len(grouped["variants"]), 2)

    def test_same_price_variants_with_different_classifications_stay_grouped(self) -> None:
        loss_html = (FIXTURES / "loss-example.html").read_text(encoding="utf-8")
        profit_html = (FIXTURES / "positive-example.html").read_text(encoding="utf-8")
        with TemporaryDirectory() as temporary_directory:
            database = Path(temporary_directory) / "rankings.sqlite3"
            with Repository(database) as repository:
                loss = parse_html(loss_html, "july-loss.html")
                loss.product_key = "sku:LOSS"
                loss.variant_key = "loss"
                loss.product_name = "July Haze in Oak"
                loss.canonical_url = "https://www.quince.com/home/july-haze"
                loss.metadata.update({"parent_product_id": "5977"})

                profit = parse_html(profit_html, "july-profit.html")
                profit.product_key = "sku:PROFIT"
                profit.variant_key = "profit"
                profit.product_name = "July Haze in Maple"
                profit.canonical_url = "https://www.quince.com/home/july-haze"
                profit.metadata.update({"parent_product_id": "5977"})
                profit.selling_price = loss.selling_price
                profit.reported_total_cost = Decimal("20.00")
                profit.calculate_metrics()

                repository.save_observation(loss)
                repository.save_observation(profit)

            result = RankingService(database).get_rankings({"view": ["all"]})

        self.assertEqual(result["total"], 1)
        grouped = result["results"][0]
        self.assertEqual(grouped["classification"], "mixed")
        self.assertEqual(grouped["variantClassifications"], ["loss", "profit"])
        self.assertTrue(grouped["metricsMixed"])
        self.assertEqual(len(grouped["variants"]), 2)

    def test_summary_buckets_partition_display_groups_exactly_once(self) -> None:
        loss_html = (FIXTURES / "loss-example.html").read_text(encoding="utf-8")
        profit_html = (FIXTURES / "positive-example.html").read_text(encoding="utf-8")
        with TemporaryDirectory() as temporary_directory:
            database = Path(temporary_directory) / "rankings.sqlite3"
            with Repository(database) as repository:
                mixed_loss = parse_html(loss_html, "july-mixed-loss.html")
                mixed_loss.product_key = "sku:MIXED-LOSS"
                mixed_loss.variant_key = "mixed-loss"
                mixed_loss.product_name = "July Haze in Oak"
                mixed_loss.canonical_url = "https://www.quince.com/home/july-haze"
                mixed_loss.metadata.update({"parent_product_id": "5977"})

                mixed_profit = parse_html(profit_html, "july-mixed-profit.html")
                mixed_profit.product_key = "sku:MIXED-PROFIT"
                mixed_profit.variant_key = "mixed-profit"
                mixed_profit.product_name = "July Haze in Maple"
                mixed_profit.canonical_url = "https://www.quince.com/home/july-haze"
                mixed_profit.selling_price = mixed_loss.selling_price
                mixed_profit.reported_total_cost = Decimal("20.00")
                mixed_profit.calculate_metrics()
                mixed_profit.metadata.update({"parent_product_id": "5977"})

                solo_loss = parse_html(loss_html, "solo-loss.html")
                solo_loss.product_key = "sku:SOLO-LOSS"
                solo_loss.variant_key = "solo-loss"
                solo_loss.canonical_url = "https://www.quince.com/bags/solo-loss"
                solo_loss.metadata.update({"parent_product_id": "SOLO-LOSS-PARENT"})

                solo_profit = parse_html(profit_html, "solo-profit.html")
                solo_profit.product_key = "sku:SOLO-PROFIT"
                solo_profit.variant_key = "solo-profit"
                solo_profit.canonical_url = "https://www.quince.com/bags/solo-profit"
                solo_profit.metadata.update({"parent_product_id": "SOLO-PROFIT-PARENT"})

                solo_break_even = parse_html(profit_html, "solo-even.html")
                solo_break_even.product_key = "sku:SOLO-EVEN"
                solo_break_even.variant_key = "solo-even"
                solo_break_even.canonical_url = "https://www.quince.com/bags/solo-even"
                solo_break_even.reported_total_cost = solo_break_even.selling_price
                solo_break_even.calculate_metrics()
                solo_break_even.metadata.update({"parent_product_id": "SOLO-EVEN-PARENT"})

                for observation in (
                    mixed_loss,
                    mixed_profit,
                    solo_loss,
                    solo_profit,
                    solo_break_even,
                ):
                    repository.save_observation(observation)

            result = RankingService(database).get_rankings({"view": ["all"]})
            summary = result["summary"]

        self.assertEqual(result["total"], 4)
        self.assertEqual(summary["total"], 4)
        self.assertEqual(summary["mixed"], 1)
        self.assertEqual(summary["losses"], 1)
        self.assertEqual(summary["profitDrivers"], 1)
        self.assertEqual(summary["breakEven"], 1)

        def assert_partition(bucket: dict[str, object], label: str) -> None:
            self.assertEqual(
                bucket["losses"] + bucket["profitDrivers"] + bucket["breakEven"] + bucket["mixed"],
                bucket["total"],
                f"{label} buckets must partition display groups exactly once",
            )

        assert_partition(summary, "summary")
        assert_partition(summary["filtered"], "filtered summary")

    def test_variants_with_different_prices_stay_separate(self) -> None:
        html = (FIXTURES / "positive-example.html").read_text(encoding="utf-8")
        with TemporaryDirectory() as temporary_directory:
            database = Path(temporary_directory) / "rankings.sqlite3"
            with Repository(database) as repository:
                small = parse_html(html, "july-small.html")
                small.product_key = "sku:LB85682"
                small.variant_key = "small"
                small.product_name = "July Haze in Oak"
                small.canonical_url = "https://www.quince.com/home/july-haze"
                small.metadata.update({"parent_product_id": "5977"})

                large = parse_html(html, "july-large.html")
                large.product_key = "sku:LB85686"
                large.variant_key = "large"
                large.product_name = "July Haze in Oak"
                large.canonical_url = "https://www.quince.com/home/july-haze"
                large.selling_price = Decimal("369.90")
                large.calculate_metrics()
                large.metadata.update({"parent_product_id": "5977"})

                repository.save_observation(small)
                repository.save_observation(large)

            result = RankingService(database).get_rankings({"view": ["all"]})

        self.assertEqual(result["total"], 2)
        self.assertEqual(
            {item["sellingPrice"] for item in result["results"]},
            {"92.00", "369.90"},
        )


if __name__ == "__main__":
    unittest.main()
