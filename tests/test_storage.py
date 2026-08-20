from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from quince_loss_leaders.parser import parse_html
from quince_loss_leaders.storage import Repository


FIXTURES = Path(__file__).parents[1] / "fixtures"


class StorageTests(unittest.TestCase):
    def test_latest_observation_is_used_for_loss_ranking(self) -> None:
        html = (FIXTURES / "loss-example.html").read_text(encoding="utf-8")
        with TemporaryDirectory() as temporary_directory:
            database = Path(temporary_directory) / "observations.sqlite3"
            with Repository(database) as repository:
                old = parse_html(
                    html,
                    "fixtures/loss-example.html",
                    captured_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
                )
                newer = parse_html(
                    html,
                    "fixtures/loss-example.html",
                    captured_at=datetime(2026, 1, 2, tzinfo=timezone.utc),
                )
                newer.selling_price = newer.selling_price + Decimal("10.00")
                newer.calculate_metrics()

                repository.save_observation(old)
                repository.save_observation(newer)
                rows = repository.loss_leaders()

            self.assertEqual(rows, [])
