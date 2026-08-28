from datetime import datetime, timezone
from decimal import Decimal
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from quince_loss_leaders.history import export_history, export_static_data, history_file_path
from quince_loss_leaders.parser import parse_html
from quince_loss_leaders.storage import Repository


FIXTURES = Path(__file__).parents[1] / "fixtures"


class HistoryExportTests(unittest.TestCase):
    def test_export_writes_product_manifest_and_history(self) -> None:
        html = (FIXTURES / "loss-example.html").read_text(encoding="utf-8")
        with TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            database = root / "rankings.sqlite3"
            output = root / "public-data"
            with Repository(database) as repository:
                first = parse_html(
                    html,
                    "loss-example.html",
                    captured_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
                )
                second = parse_html(
                    html,
                    "loss-example.html",
                    captured_at=datetime(2026, 1, 2, tzinfo=timezone.utc),
                )
                second.selling_price = second.selling_price + Decimal("10.00")
                second.calculate_metrics()
                repository.save_observation(first)
                repository.save_observation(second)

            summary = export_static_data(database, output)
            manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
            entry = manifest["products"][0]
            detail = json.loads((output / entry["historyPath"]).read_text(encoding="utf-8"))
            rankings = json.loads((output / "rankings.json").read_text(encoding="utf-8"))

            self.assertEqual(summary.product_count, 1)
            self.assertEqual(summary.observation_count, 2)
            self.assertEqual(summary.ranking_count, 1)
            self.assertEqual(entry["name"], "Example Recycled Tote")
            self.assertEqual(entry["observationCount"], 2)
            self.assertEqual(detail["history"][0]["sellingPrice"], "29.99")
            self.assertEqual(detail["history"][1]["sellingPrice"], "39.99")
            self.assertEqual(detail["history"][0]["unitSpread"], "-2.01")
            self.assertEqual(detail["current"]["sellingPrice"], "39.99")
            self.assertEqual(rankings["schemaVersion"], 1)
            self.assertEqual(rankings["results"][0]["historyPath"], entry["historyPath"])

    def test_export_merge_keeps_existing_history_and_deduplicates_reruns(self) -> None:
        html = (FIXTURES / "loss-example.html").read_text(encoding="utf-8")
        with TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            output = root / "public-data"
            first_database = root / "first.sqlite3"
            second_database = root / "second.sqlite3"

            first = parse_html(
                html,
                "loss-example.html",
                captured_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            )
            with Repository(first_database) as repository:
                repository.save_observation(first)
            export_history(first_database, output)

            second = parse_html(
                html,
                "loss-example.html",
                captured_at=datetime(2026, 1, 2, tzinfo=timezone.utc),
            )
            second.selling_price = second.selling_price + Decimal("10.00")
            second.calculate_metrics()
            with Repository(second_database) as repository:
                repository.save_observation(second)

            merged = export_history(second_database, output)
            rerun = export_history(second_database, output)
            manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
            detail = json.loads((output / manifest["products"][0]["historyPath"]).read_text(encoding="utf-8"))

            self.assertEqual(merged.observation_count, 2)
            self.assertEqual(rerun.observation_count, 2)
            self.assertEqual(len(detail["history"]), 2)

    def test_history_file_path_is_stable_for_product_variant(self) -> None:
        first = history_file_path("sku:EXAMPLE", "color:red")
        second = history_file_path("sku:EXAMPLE", "color:red")
        different = history_file_path("sku:EXAMPLE", "color:blue")

        self.assertEqual(first, second)
        self.assertNotEqual(first, different)
        self.assertTrue(first.startswith("history/"))


if __name__ == "__main__":
    unittest.main()
