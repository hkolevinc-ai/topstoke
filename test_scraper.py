import unittest

from scraper import (
    Config,
    OutputRow,
    Product,
    TemuTemplate,
    age_group_for,
    classify_kind,
    extract_size_from_product_name,
    extract_variant_size,
    normalize_size,
    product_to_rows,
)


def product(name: str, category: str, url: str, variants=None) -> Product:
    return Product(
        url=url,
        product_id="123",
        name=name,
        category_path=category,
        description="Памучен продукт",
        bullets=[],
        main_images=["https://topstokee.com/image.jpg"],
        detail_images=[],
        price=20.0,
        list_price=25.0,
        variants=variants or [{"id": "1", "parameters": {}, "price": 20.0, "list_price": 25.0}],
    )


class SizeTests(unittest.TestCase):
    def test_cyrillic_m_is_latin_m(self):
        self.assertEqual(normalize_size("М")[:3], ("2 - Regular Size", "10 - Alpha", "M"))

    def test_age_ranges_are_normalized_as_exact_custom_sizes(self):
        self.assertEqual(normalize_size("9/11г.")[:3], ("101 - Custom size", "10 - Alpha", "9-11Y"))
        self.assertEqual(normalize_size("12/13г.")[:3], ("101 - Custom size", "10 - Alpha", "12-13Y"))
        self.assertEqual(age_group_for("9-11Y"), "12 and under")
        self.assertEqual(age_group_for("12-13Y"), "13 years and above")

    def test_gendered_sizes_become_one_custom_combination(self):
        params = {"Мъжки Размер": "S.", "Дамски Размер": "2XL"}
        self.assertEqual(extract_variant_size(params, "Тениски за двойки"), "Men S / Women XXL")
        rows, reason = product_to_rows(
            product(
                "Тениски За Двойки Stitch and Angel",
                "ЗА ДВОЙКИ > Тениски",
                "https://topstokee.com/product/teniski-za-dvoyki-stitch-and-angel",
                [{"id": "61110", "parameters": params, "price": 25.56, "list_price": 35.07}],
            ),
            Config(),
        )
        self.assertIsNone(reason)
        self.assertEqual(rows[0].temu_size, "Men S / Women XXL")
        self.assertEqual(rows[0].size_family, "101 - Custom size")

    def test_fixed_outlet_size_is_read_from_title(self):
        name = "[ РАЗПРОДАЖБА ] Тениска Мафия 14 [ размер: 3XL ]"
        self.assertEqual(extract_size_from_product_name(name), "3XL")
        rows, _ = product_to_rows(
            product(name, "РАЗПРОДАЖБА > ТЕНИСКИ", "https://topstokee.com/product/sale"),
            Config(),
        )
        self.assertEqual(rows[0].temu_size, "XXXL")

    def test_age_range_measurements_use_height_equivalents(self):
        base = dict(
            source_url="u", source_category="ЗА ДЕЦА", category_id="30847",
            category_key="sweatshirt_kids", product_id="1", parent_sku="p", sku="s",
            name="n", description="d", bullets=[], main_images=[], detail_images=[],
            size_raw="12/13г.", size_family="101 - Custom size", sub_size_family="10 - Alpha",
            temu_size="12-13Y", color="Multicolor", price=1.0, list_price=2.0, quantity=10,
            composition={"Cotton": 80.0, "Polyester": 20.0}, product_kind="sweatshirt",
            is_kids=True, age_group="13 years and above",
        )
        item = OutputRow(**base)
        self.assertEqual(TemuTemplate.measurement_value("Tops - Product - Chest", item), 49.0)
        self.assertEqual(TemuTemplate.measurement_value("Tops - Product - Length", item), 60.0)


class CategoryTests(unittest.TestCase):
    def test_child_hat_wins_over_combined_category_name(self):
        item = product(
            "Детска Шапка Ballerina Cappuccina",
            "ЗА ДЕЦА > ШАПКИ И РАНИЦИ",
            "https://topstokee.com/product/detska-shapka-ballerina-cappuccina",
        )
        self.assertEqual(classify_kind(item), "hat")

    def test_backpack_is_still_skipped(self):
        item = product(
            "Детска Раница Stitch",
            "ЗА ДЕЦА > ШАПКИ И РАНИЦИ",
            "https://topstokee.com/product/detska-ranitsa-stitch",
        )
        self.assertIsNone(classify_kind(item))


if __name__ == "__main__":
    unittest.main()
