from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from quince_loss_leaders.parser import parse_html
from quince_loss_leaders.storage import Repository


FIXTURES = Path(__file__).parents[1] / "fixtures"


class StorageTests(unittest.TestCase):
    def test_read_only_repository_requires_existing_database(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            database = Path(temporary_directory) / "missing.sqlite3"

            with self.assertRaises(FileNotFoundError):
                Repository(database, read_only=True)

            self.assertFalse(database.exists())

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

    def test_rankings_and_profit_drivers_use_latest_complete_rows(self) -> None:
        loss_html = (FIXTURES / "loss-example.html").read_text(encoding="utf-8")
        positive_html = (FIXTURES / "positive-example.html").read_text(encoding="utf-8")
        with TemporaryDirectory() as temporary_directory:
            database = Path(temporary_directory) / "observations.sqlite3"
            with Repository(database) as repository:
                repository.save_observation(
                    parse_html(
                        loss_html,
                        "fixtures/loss-example.html",
                        captured_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
                    )
                )
                repository.save_observation(
                    parse_html(
                        positive_html,
                        "fixtures/positive-example.html",
                        captured_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
                    )
                )

                rankings = repository.rankings()
                profit_drivers = repository.profit_drivers()

            self.assertEqual([row.name for row in rankings], [
                "Example Recycled Tote",
                "Example Carry-All Tote",
            ])
            self.assertEqual([row.name for row in profit_drivers], [
                "Example Carry-All Tote",
            ])

    def test_historical_observations_retain_each_capture_and_cost_lines(self) -> None:
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
                history = repository.historical_observations(
                    product_key=old.product_key,
                )

            self.assertEqual(len(history), 2)
            self.assertEqual(
                [observation.captured_at for observation in history],
                [
                    datetime(2026, 1, 1, tzinfo=timezone.utc),
                    datetime(2026, 1, 2, tzinfo=timezone.utc),
                ],
            )
            self.assertEqual(history[0].unit_spread, Decimal("-2.01"))
            self.assertEqual(history[1].unit_spread, Decimal("7.99"))
            self.assertEqual(len(history[0].cost_lines), 6)
