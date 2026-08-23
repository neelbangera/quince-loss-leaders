from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from quince_loss_leaders.api import RankingService
from quince_loss_leaders.parser import parse_html
from quince_loss_leaders.storage import Repository


FIXTURES = Path(__file__).parents[1] / "fixtures"


class ApiTests(unittest.TestCase):
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

    def test_display_name_removes_color_and_flags_large_fee(self) -> None:
        html = """
        <html><head>
          <link rel="canonical" href="https://example.test/men/example-chair">
          <meta property="product:price:amount" content="20.00">
          <script type="application/ld+json">
            {"@type":"Product","name":"Example Chair in Performance Velvet in Charcoal","sku":"EX-FEE-001"}
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


if __name__ == "__main__":
    unittest.main()
