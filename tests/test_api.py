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

    def test_invalid_query_is_rejected(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            service = RankingService(Path(temporary_directory) / "rankings.sqlite3")
            with self.assertRaises(ValueError):
                service.get_rankings({"view": ["unknown"]})


if __name__ == "__main__":
    unittest.main()
