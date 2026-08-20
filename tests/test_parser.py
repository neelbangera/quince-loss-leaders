from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
import unittest

from quince_loss_leaders.parser import parse_html


FIXTURES = Path(__file__).parents[1] / "fixtures"


def read_fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


class ParserTests(unittest.TestCase):
    def test_extracts_cost_breakdown_and_loss(self) -> None:
        observation = parse_html(
            read_fixture("loss-example.html"),
            "fixtures/loss-example.html",
            captured_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )

        self.assertEqual(observation.product_name, "Example Recycled Tote")
        self.assertEqual(observation.selling_price, Decimal("29.99"))
        self.assertEqual(observation.reported_total_cost, Decimal("32.00"))
        self.assertEqual(observation.unit_spread, Decimal("-2.01"))
        self.assertEqual(observation.classification, "loss")
        self.assertTrue(observation.is_rankable)
        self.assertEqual(len(observation.cost_lines), 6)

    def test_positive_observation_is_not_a_loss(self) -> None:
        observation = parse_html(read_fixture("positive-example.html"), "fixtures/positive-example.html")

        self.assertEqual(observation.parse_status, "complete")
        self.assertEqual(observation.unit_spread, Decimal("11.10"))
        self.assertEqual(observation.classification, "positive")

    def test_zero_cost_placeholder_is_not_rankable(self) -> None:
        observation = parse_html(read_fixture("zero-placeholder.html"), "fixtures/zero-placeholder.html")

        self.assertEqual(observation.parse_status, "invalid")
        self.assertFalse(observation.is_rankable)
        self.assertIn("zero_cost_placeholder", {issue.code for issue in observation.issues})

    def test_supports_div_based_cost_layout(self) -> None:
        html = """
        <html><head><meta property="product:price:amount" content="10.00"></head>
        <body><h1>Div Layout Product</h1>
        <section>
          <div>Materials</div><div>$3.00</div>
          <div>Crafting Cost</div><div>$4.00</div>
          <div>Packaging</div><div>$1.00</div>
          <div>Freight &amp; Handling</div><div>$2.00</div>
          <div>Credit Card Fees</div><div>$0.50</div>
          <div>Duties, Taxes, And Fees</div><div>$1.50</div>
          <div>TOTAL COST</div><div>$12.00</div>
        </section></body></html>
        """
        observation = parse_html(html, "div-layout.html")

        self.assertEqual(observation.parse_status, "complete")
        self.assertEqual(observation.unit_spread, Decimal("-2.00"))
