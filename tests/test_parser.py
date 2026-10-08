from datetime import datetime, timezone
from decimal import Decimal
import json
from pathlib import Path
import unittest

from quince_loss_leaders.parser import parse_html, parse_money


FIXTURES = Path(__file__).parents[1] / "fixtures"


def read_fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


class ParserTests(unittest.TestCase):
    def test_parses_four_digit_money_without_truncating(self) -> None:
        self.assertEqual(parse_money("$1300.00"), Decimal("1300.00"))
        self.assertEqual(parse_money("$1,300.00"), Decimal("1300.00"))

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

    def test_extracts_product_images_from_structured_and_html_metadata(self) -> None:
        html = """
        <html><head>
          <link rel="canonical" href="https://www.quince.com/men/image-product">
          <meta property="og:image" content="/images/og-product.jpg">
          <script type="application/ld+json">
            {"@type":"Product","name":"Image Product","image":["https://cdn.example.com/front.jpg","/images/back.jpg"]}
          </script>
        </head><body>
          <img data-src="/images/lazy-product.jpg" alt="Image Product">
        </body></html>
        """

        observation = parse_html(html, "image-product.html")

        self.assertEqual(
            observation.metadata["image_urls"],
            [
                "https://cdn.example.com/front.jpg",
                "https://www.quince.com/images/back.jpg",
                "https://www.quince.com/images/og-product.jpg",
                "https://www.quince.com/images/lazy-product.jpg",
            ],
        )
        self.assertEqual(observation.metadata["image_url"], "https://cdn.example.com/front.jpg")

    def test_ignores_ui_images_and_recommendation_products(self) -> None:
        html = """
        <html><head>
          <link rel="canonical" href="https://www.quince.com/men/image-product">
          <script type="application/ld+json">
            {"@type":"Product","name":"Image Product","image":"https://cdn.example.com/main.jpg"}
          </script>
          <script type="application/ld+json">
            {"@type":"Product","name":"Recommended Product","image":"https://cdn.example.com/recommended.jpg"}
          </script>
        </head><body>
          <img src="https://cdn.example.com/privacyoptions123x59.png">
          <img src="https://cdn.example.com/Logo.png">
          <img src="https://cdn.example.com/blue_checkbox.png">
          <img src="https://cdn.example.com/check_in_dark_green.jpg">
        </body></html>
        """

        observation = parse_html(html, "image-filtering.html")

        self.assertEqual(
            observation.metadata["image_urls"],
            [
                "https://cdn.example.com/main.jpg",
                "https://cdn.example.com/check_in_dark_green.jpg",
            ],
        )

    def test_normalizes_duties_above_the_rest_of_cost(self) -> None:
        html = """
        <html><head><meta property="product:price:amount" content="100.00"></head>
        <body><h1>Fee Check Product</h1><table>
          <tr><td>Materials</td><td>$12.00</td></tr>
          <tr><td>Crafting Cost</td><td>$8.00</td></tr>
          <tr><td>Duties, Taxes, And Fees</td><td>$21.00</td></tr>
          <tr><td>TOTAL COST</td><td>$41.00</td></tr>
        </table></body></html>
        """

        observation = parse_html(html, "fee-normalization.html")
        duty_line = next(
            line for line in observation.cost_lines if line.normalized_type == "duties_taxes_fees"
        )

        self.assertEqual(duty_line.amount, Decimal("0.00"))
        self.assertEqual(observation.reported_total_cost, Decimal("20.00"))
        self.assertEqual(observation.unit_spread, Decimal("80.00"))
        self.assertEqual(observation.total_cost_source, "normalized_fee_excluded")
        self.assertTrue(observation.metadata["fee_warning"])
        self.assertIn("normalized_exorbitant_fee", {issue.code for issue in observation.issues})

    def test_normalizes_freight_above_the_selling_price(self) -> None:
        # Mirrors the captured Solid Wood Midcentury Platform Bed: the source
        # discloses shippingHandling of 4580.83 against a 1300.00 price, which
        # turned a profitable item into the catalog's worst "loss leader".
        html = """
        <html><head><meta property="product:price:amount" content="1300.00"></head>
        <body><h1>Freight Check Bed</h1><table>
          <tr><td>Materials</td><td>$205.80</td></tr>
          <tr><td>Crafting Cost</td><td>$34.30</td></tr>
          <tr><td>Packaging</td><td>$34.30</td></tr>
          <tr><td>Freight &amp; Handling</td><td>$4580.83</td></tr>
          <tr><td>Credit Card Fees</td><td>$30.13</td></tr>
          <tr><td>Duties, Taxes, And Fees</td><td>$42.88</td></tr>
          <tr><td>TOTAL COST</td><td>$4928.24</td></tr>
        </table></body></html>
        """

        observation = parse_html(html, "freight-anomaly.html")
        freight_line = next(
            line for line in observation.cost_lines if line.normalized_type == "freight_handling"
        )
        materials_line = next(
            line for line in observation.cost_lines if line.normalized_type == "materials"
        )

        self.assertEqual(freight_line.amount, Decimal("0.00"))
        self.assertEqual(materials_line.amount, Decimal("205.80"))
        self.assertEqual(observation.reported_total_cost, Decimal("347.41"))
        self.assertEqual(observation.unit_spread, Decimal("952.59"))
        self.assertGreater(observation.unit_spread, 0)
        self.assertTrue(observation.metadata["fee_warning"])
        self.assertEqual(
            observation.metadata["fee_normalization"]["rule"], "exceeds_selling_price"
        )
        self.assertEqual(
            observation.metadata["fee_normalization"]["original_amount"], "4580.83"
        )
        self.assertIn("normalized_exorbitant_fee", {issue.code for issue in observation.issues})

    def test_target_variant_key_selects_that_embedded_variant(self) -> None:
        # A reparse must be able to state which variant it is reinterpreting
        # without guessing. Two variants here differ only by colour and share
        # identical economics; the default selection would pick the second.
        next_data = {
            "props": {
                "pageProps": {
                    "pageData": {
                        "context": {
                            "pageDataJson": {
                                "widgets": [
                                    {
                                        "data": {
                                            "transparentPricingData": {
                                                "products": {
                                                    "6685": {
                                                        "productId": "6685",
                                                        "variants": [
                                                            {
                                                                "variantId": 151402,
                                                                "name": "One Size / Cypress",
                                                                "totalPrice": 525,
                                                                "materials": 94.8,
                                                                "crafting": 15.8,
                                                                "packaging": 15.8,
                                                                "creditCardFees": 11.89,
                                                                "dutyFee": 39.5,
                                                                "shippingHandling": 883,
                                                            },
                                                            {
                                                                "variantId": 105329,
                                                                "name": "One Size / Dune",
                                                                "totalPrice": 525,
                                                                "materials": 94.8,
                                                                "crafting": 15.8,
                                                                "packaging": 15.8,
                                                                "creditCardFees": 11.89,
                                                                "dutyFee": 39.5,
                                                                "shippingHandling": 883,
                                                            },
                                                        ],
                                                    }
                                                }
                                            }
                                        }
                                    }
                                ]
                            }
                        }
                    }
                }
            }
        }
        html = (
            '<html><head><meta property="product:price:amount" content="525.00">'
            f"<script id=\"__NEXT_DATA__\" type=\"application/json\">{json.dumps(next_data)}</script>"
            "</head><body><h1>Swivel Chair</h1></body></html>"
        )

        defaulted = parse_html(html, "chair.html")
        targeted = parse_html(html, "chair.html", target_variant_key="105329")

        # With no variant evidence the first embedded variant wins.
        self.assertEqual(defaulted.variant_key, "151402")
        # An explicit target overrides that default through the existing
        # ?variant=<id> score, without touching variant selection logic.
        self.assertEqual(targeted.variant_key, "105329")
        self.assertEqual(targeted.unit_spread, Decimal("347.21"))
        self.assertTrue(targeted.metadata["fee_warning"])

    def test_keeps_primary_cost_above_the_price_as_a_real_loss(self) -> None:
        # A hand-tufted rug at $59.90 with $248 of materials is the *definition*
        # of a loss leader, not a parse error. Materials and crafting are the
        # cost of the thing itself and must never be normalised away.
        html = """
        <html><head><meta property="product:price:amount" content="59.90"></head>
        <body><h1>Rug Loss Leader</h1><table>
          <tr><td>Materials</td><td>$248.00</td></tr>
          <tr><td>Crafting Cost</td><td>$200.00</td></tr>
          <tr><td>Freight &amp; Handling</td><td>$29.00</td></tr>
          <tr><td>Packaging</td><td>$2.00</td></tr>
          <tr><td>TOTAL COST</td><td>$479.15</td></tr>
        </table></body></html>
        """

        observation = parse_html(html, "rug-loss-leader.html")
        materials_line = next(
            line for line in observation.cost_lines if line.normalized_type == "materials"
        )

        self.assertEqual(materials_line.amount, Decimal("248.00"))
        self.assertEqual(observation.reported_total_cost, Decimal("479.15"))
        self.assertEqual(observation.unit_spread, Decimal("-419.25"))
        self.assertNotIn("fee_warning", observation.metadata)

    def test_leaves_small_freight_alone(self) -> None:
        # Freight legitimately dominates cost on cheap garments. A $20 dress
        # with $15.09 of allocated shipping must not be normalised away -- doing
        # so would understate cost and invent a profit.
        html = """
        <html><head><meta property="product:price:amount" content="20.00"></head>
        <body><h1>Freight Check Dress</h1><table>
          <tr><td>Materials</td><td>$2.50</td></tr>
          <tr><td>Crafting Cost</td><td>$1.16</td></tr>
          <tr><td>Freight &amp; Handling</td><td>$15.09</td></tr>
          <tr><td>TOTAL COST</td><td>$18.75</td></tr>
        </table></body></html>
        """

        observation = parse_html(html, "freight-normal.html")
        freight_line = next(
            line for line in observation.cost_lines if line.normalized_type == "freight_handling"
        )

        self.assertEqual(freight_line.amount, Decimal("15.09"))
        self.assertEqual(observation.reported_total_cost, Decimal("18.75"))
        self.assertEqual(observation.unit_spread, Decimal("1.25"))
        self.assertNotIn("fee_warning", observation.metadata)

    def test_extracts_embedded_transparent_pricing(self) -> None:
        next_data = {
            "props": {
                "pageProps": {
                    "pageData": {
                        "context": {
                            "pageDataJson": {
                                "widgets": [
                                    {
                                        "data": {
                                            "transparentPricingData": {
                                                "products": {
                                                    "1848": {
                                                        "variants": [
                                                            {"name": "One Size / Mulberry"},
                                                            {
                                                                "name": "One Size / Charcoal",
                                                                "variantId": 45780,
                                                                "totalPrice": 92,
                                                                "materials": 6.21,
                                                                "hardware": 11.80,
                                                                "crafting": 14.23,
                                                                "packaging": 1.76,
                                                                "shippingHandling": 15.58,
                                                                "creditCardFees": 2.45,
                                                                "dutyFee": 18.73,
                                                            },
                                                        ]
                                                    }
                                                }
                                            }
                                        }
                                    }
                                ]
                            }
                        }
                    }
                }
            }
        }
        html = f"""
        <html><head>
          <meta property="product:price:amount" content="92.00">
        </head><body>
          <h1>Embedded Tote</h1>
          <script id="__NEXT_DATA__" type="application/json">
            {json.dumps(next_data)}
          </script>
        </body></html>
        """

        observation = parse_html(
            html,
            "embedded-pricing.html",
            canonical_url="https://www.quince.com/tote?color=charcoal",
        )

        self.assertEqual(observation.parse_status, "complete")
        self.assertEqual(observation.variant_key, "45780")
        self.assertEqual(observation.cost_lines[0].amount, Decimal("18.01"))
        self.assertEqual(observation.reported_total_cost, Decimal("70.76"))
        self.assertEqual(observation.unit_spread, Decimal("21.24"))
        self.assertEqual(observation.total_cost_source, "embedded_inferred")

    def test_matches_embedded_variant_to_selected_jsonld_offer(self) -> None:
        next_data = {
            "props": {
                "pageProps": {
                    "transparentPricingData": {
                        "products": {
                            "5977": {
                                "variants": [
                                    {
                                        "name": '21.25"x26.25" / Oak',
                                        "variantId": 70343,
                                        "materials": 56.99,
                                        "hardware": 6.48,
                                        "crafting": 64.76,
                                        "packaging": 6.48,
                                        "shippingHandling": 14.62,
                                        "creditCardFees": 4.08,
                                        "dutyFee": 0,
                                    },
                                    {
                                        "name": '21.25"x26.25" / Maple',
                                        "variantId": 70344,
                                        "materials": 56.99,
                                        "hardware": 6.48,
                                        "crafting": 64.76,
                                        "packaging": 6.48,
                                        "shippingHandling": 16.48,
                                        "creditCardFees": 4.08,
                                        "dutyFee": 0,
                                    },
                                ]
                            }
                        }
                    }
                }
            }
        }
        html = f"""
        <html><head>
          <script type="application/ld+json">
            {{"@type":"Product","name":"July Haze in Maple","sku":"LB85683",
              "offers":{{"price":"179.90","priceCurrency":"USD",
                "url":"https://www.quince.com/home/july-haze?color=maple&size=21.25%22x26.25%22"}}}}
          </script>
          <script id="__NEXT_DATA__" type="application/json">
            {json.dumps(next_data)}
          </script>
        </head><body></body></html>
        """

        observation = parse_html(html, "july-haze-maple.html")

        self.assertEqual(observation.sku, "LB85683")
        self.assertEqual(observation.variant_key, "70344")
        self.assertEqual(observation.metadata["variant_color"], "Maple")
        self.assertEqual(observation.metadata["variant_size"], '21.25"x26.25"')
        self.assertEqual(observation.metadata["parent_product_id"], "5977")
        self.assertEqual(observation.reported_total_cost, Decimal("155.27"))
