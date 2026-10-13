from __future__ import annotations

import unittest

from quince_loss_leaders.taxonomy import infer_taxonomy


def place(url: str, name: str) -> tuple[str, str]:
    taxonomy = infer_taxonomy(f"https://www.quince.com{url}", name)
    return taxonomy.department, taxonomy.category


class TaxonomyTests(unittest.TestCase):
    def test_the_last_noun_names_the_product(self) -> None:
        cases = {
            ("/men/mens-performance-wrinkle-free-dress-shirt", "Performance Stretch Wrinkle-Free Dress Shirt in White"): ("men", "tops"),
            ("/men/stretch-wool-dress-pant", "Stretch Wool Dress Pant in Grey Melange"): ("men", "pants"),
            ("/men/100-organic-cotton-terry-towel-polo", "100% Organic Cotton Terry Towel Polo in Navy"): ("men", "tops"),
            ("/women/silk/silk-shirt-dress", "Washable Stretch Silk Shirt Dress in Black"): ("women", "dresses"),
            ("/women/baby-alpaca-wool-diamond-stitch-crew", "Baby Alpaca-Wool Diamond Stitch Crew in Ivory"): ("women", "sweaters"),
            ("/home/mulberry-silk-flat-sheet", "100% Mulberry Silk Flat Sheet in Ivory"): ("home", "bedding"),
            ("/home/top-grain-leather-barrel-back-dining-chair", "Top Grain Leather Barrel Back Dining Chair in Cognac"): ("home", "furniture"),
            ("/unisex/unisex-alpaca-boot-socks-3-pack", "Alpaca Boot Socks (3-Pack) in Grey"): ("unisex", "accessories"),
        }
        for (url, name), expected in cases.items():
            with self.subTest(name=name):
                self.assertEqual(place(url, name), expected)

    def test_a_phrase_outranks_the_word_it_ends_with(self) -> None:
        self.assertEqual(place("/home/european-linen-bed-skirt-15", 'European Linen Bed Skirt 15"'), ("home", "bedding"))
        self.assertEqual(place("/home/european-linen-gingham-table-runner", "European Linen Gingham Table Runner"), ("home", "kitchen-dining"))
        self.assertEqual(place("/home/white-lotus-tea-room-spray", "White Lotus Tea Room Spray"), ("home", "home-decor"))
        self.assertEqual(place("/home/italian-leather-braided-key-ring-2-pack", "Italian Leather Braided Key Ring (2-Pack)"), ("home", "accessories"))

    def test_a_colour_is_not_the_product(self) -> None:
        self.assertEqual(place("/women/tencel-rib-knit-lounge-boxer", "Tencel Rib Knit Lounge Boxer (3-pack) in Wine"), ("women", "sleep-underwear"))
        self.assertEqual(place("/women/italian-leather-diamond-stitch-sling", "Italian Leather Diamond Stitch Sling in Cream"), ("women", "bags"))

    def test_plurals_match_their_singular(self) -> None:
        self.assertEqual(place("/women/linen-shorts", "100% European Linen Shorts in Black"), ("women", "shorts"))
        self.assertEqual(place("/women/diamond-studs", "14K Gold Diamond Studs in Yellow Gold"), ("women", "jewelry"))
        self.assertEqual(place("/home/steak-knives", "Stainless Steel Steak Knives, Set of 4"), ("home", "kitchen-dining"))

    def test_what_follows_with_describes_the_product(self) -> None:
        self.assertEqual(
            place("/home/chenille-dining-chair", "Performance Chenille Dining Chair with Powder Coated Iron Legs in Snow"),
            ("home", "furniture"),
        )

    def test_a_credited_print_is_home_decor_whatever_the_artist_is_called(self) -> None:
        self.assertEqual(place("/home/halleys-comet", "Halley's Comet by Sarah Short in Maple"), ("home", "home-decor"))

    def test_a_robe_follows_its_department(self) -> None:
        self.assertEqual(place("/women/maternity-bamboo-jersey-robe", "Bamboo Jersey Maternity Robe"), ("women", "sleep-underwear"))
        self.assertEqual(place("/home/turkish-cotton-robe", "Organic Turkish Cotton Robe in White"), ("home", "bath"))

    def test_childrens_items_filed_elsewhere_are_baby_and_kids(self) -> None:
        self.assertEqual(place("/unisex/kid-organic-cotton-sleeveless-ruffle-dress", "Organic Cotton Sleeveless Ruffle Dress")[0], "baby-kids")
        self.assertEqual(place("/home/baby-and-kids/recycled-double-pocket-backpack", "Recycled Double Pocket Backpack - Medium")[0], "baby-kids")
        self.assertEqual(place("/washable-cashmere-pointelle-cardigan-toddler", "Mongolian Cashmere Pointelle Cardigan")[0], "baby-kids")
        # "Baby Alpaca" is a fibre, so an adult beanie stays where Quince filed it.
        self.assertEqual(place("/unisex/baby-alpaca-beanie", "Baby Alpaca Beanie in Oatmeal")[0], "unisex")

    def test_department_follows_the_first_path_segment(self) -> None:
        self.assertEqual(place("/beauty/eau-de-parfum-discovery-set", "Eau de Parfum Discovery Set"), ("beauty-wellness", "beauty"))
        self.assertEqual(place("/accessories/mens-italian-leather-bifold-wallet", "Italian Leather Bifold Wallet in Black"), ("men", "bags"))

    def test_an_unrecognised_product_is_other_not_a_guess(self) -> None:
        self.assertEqual(place("/pickleball-set", "Two Paddle Pickleball Set in Sage/Cantaloupe"), ("other", "other"))

    def test_a_stored_category_still_wins(self) -> None:
        taxonomy = infer_taxonomy("https://www.quince.com/men/dress-shirt", "Dress Shirt", "Shirts")
        self.assertEqual((taxonomy.category, taxonomy.source), ("shirts", "stored"))


if __name__ == "__main__":
    unittest.main()
