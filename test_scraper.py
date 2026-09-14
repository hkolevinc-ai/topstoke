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
    grouped_chunks,
    normalize_size,
    product_to_rows,
    validate_output_rows,
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

    def test_his_and_hers_size_labels_are_recognized(self):
        params = {"Размер за него": "S", "Размер за нея": "M"}
        self.assertEqual(extract_variant_size(params, "Суичъри за двойки"), "Men S / Women M")

    def test_unusual_couple_size_keys_still_create_one_unique_size(self):
        params = {"Първа дреха": "S", "Втора дреха": "2XL"}
        self.assertEqual(
            extract_variant_size(params, "Блузи за двойки"),
            "Първа дреха S / Втора дреха XXL",
        )

    def test_different_adult_size_parameters_create_separate_parents(self):
        rows, reason = product_to_rows(
            product(
                "Тениска България",
                "ТЕНИСКИ",
                "https://topstokee.com/product/teniska-balgariya",
                [
                    {"id": "1", "parameters": {"Мъжки размер": "S"}, "price": 20.0, "list_price": 25.0},
                    {"id": "2", "parameters": {"Дамски размер": "S"}, "price": 20.0, "list_price": 25.0},
                ],
            ),
            Config(),
        )
        self.assertIsNone(reason)
        self.assertEqual(len(rows), 2)
        self.assertEqual(len({row.parent_sku for row in rows}), 2)
        self.assertEqual({row.category_id for row in rows}, {"30469", "29069"})
        self.assertTrue(any("Мъжки" in row.name for row in rows))
        self.assertTrue(any("Дамски" in row.name for row in rows))

    def test_model_parameter_creates_separate_parents(self):
        rows, _ = product_to_rows(
            product(
                "Тениска Металика",
                "ТЕНИСКИ",
                "https://topstokee.com/product/teniska-metalika",
                [
                    {"id": "1", "parameters": {"Размер": "M", "Модел": "Мъжка"}, "price": 20.0, "list_price": 25.0},
                    {"id": "2", "parameters": {"Размер": "M", "Модел": "Дамска"}, "price": 20.0, "list_price": 25.0},
                ],
            ),
            Config(),
        )
        self.assertEqual(len({row.parent_sku for row in rows}), 2)
        self.assertEqual({row.variant_group for row in rows}, {"Мъжка", "Дамска"})

    def test_flexible_color_label_is_recognized(self):
        rows, _ = product_to_rows(
            product(
                "Тениска",
                "ТЕНИСКИ",
                "https://topstokee.com/product/teniska",
                [{"id": "1", "parameters": {"Размер": "M", "Избери цвят": "Черен"}, "price": 20.0, "list_price": 25.0}],
            ),
            Config(),
        )
        self.assertEqual(rows[0].color, "Черен")

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
            category_key="sweatshirt_boys", product_id="1", parent_sku="p", sku="s",
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

    def test_womens_tshirt_uses_womens_category(self):
        rows, reason = product_to_rows(
            product(
                "Дамска тениска България",
                "ТЕНИСКИ",
                "https://topstokee.com/product/damska-teniska",
                [{"id": "1", "parameters": {"Дамски размер": "M"}, "price": 20.0, "list_price": 25.0}],
            ),
            Config(),
        )
        self.assertIsNone(reason)
        self.assertEqual(rows[0].category_id, "29069")
        self.assertEqual(rows[0].category_key, "tshirt_women")

    def test_girls_hoodie_uses_girls_hoodie_category(self):
        item = product(
            "Детски суичър за момиче",
            "ЗА ДЕЦА > СУИЧЪРИ",
            "https://topstokee.com/product/momiche-hoodie",
            [{"id": "1", "parameters": {"Размер": "128"}, "price": 20.0, "list_price": 25.0}],
        )
        item.description = "Памучен суичър с качулка"
        rows, reason = product_to_rows(item, Config())
        self.assertIsNone(reason)
        self.assertEqual(rows[0].category_id, "29690")
        self.assertEqual(rows[0].category_key, "hoodie_girls")

    def test_boys_hoodie_uses_hoodie_not_sweatshirt_category(self):
        item = product(
            "Детски суичър за момче",
            "ЗА ДЕЦА > СУИЧЪРИ",
            "https://topstokee.com/product/momche-hoodie",
            [{"id": "1", "parameters": {"Размер": "128"}, "price": 20.0, "list_price": 25.0}],
        )
        item.description = "Памучен суичър с качулка"
        rows, reason = product_to_rows(item, Config())
        self.assertIsNone(reason)
        self.assertEqual(rows[0].category_id, "30846")
        self.assertEqual(rows[0].category_key, "hoodie_boys")

    def test_explicit_girls_sweatshirt_is_skipped_without_exact_category(self):
        rows, reason = product_to_rows(
            product(
                "Суичър За Момиченце Mini Dragon 2",
                "ЗА ДЕЦА > СУИЧЪРИ",
                "https://topstokee.com/product/suichar-za-momichence-mini-dragon-2",
                [{"id": "1", "parameters": {"Размер": "128"}, "price": 20.0, "list_price": 25.0}],
            ),
            Config(),
        )
        self.assertEqual(rows, [])
        self.assertIn("girls/sweatshirt", reason)

    def test_child_hat_is_skipped_without_child_hat_category(self):
        rows, reason = product_to_rows(
            product(
                "Детска Шапка Ballerina Cappuccina",
                "ЗА ДЕЦА > ШАПКИ И РАНИЦИ",
                "https://topstokee.com/product/detska-shapka-ballerina-cappuccina",
            ),
            Config(),
        )
        self.assertEqual(rows, [])
        self.assertIn("boys/hat", reason)

    def test_womens_hat_uses_womens_category(self):
        rows, reason = product_to_rows(
            product(
                "Дамска шапка с козирка",
                "ШАПКИ",
                "https://topstokee.com/product/damska-shapka",
            ),
            Config(),
        )
        self.assertIsNone(reason)
        self.assertEqual(rows[0].category_id, "29270")


class ExportSafetyTests(unittest.TestCase):
    @staticmethod
    def row(parent: str, sku: str, size: str = "M", color: str = "Black") -> OutputRow:
        return OutputRow(
            source_url="https://topstokee.com/product/test",
            source_category="ТЕНИСКИ",
            category_id="30469",
            category_key="tshirt_men",
            product_id="1",
            parent_sku=parent,
            sku=sku,
            name="Test",
            description="Description",
            bullets=[],
            main_images=["https://topstokee.com/image.jpg"],
            detail_images=[],
            size_raw=size,
            size_family="2 - Regular Size",
            sub_size_family="10 - Alpha",
            temu_size=size,
            color=color,
            price=10.0,
            list_price=12.0,
            quantity=10,
            composition={"Cotton": 100.0},
            product_kind="tshirt",
            is_kids=False,
            age_group="13 years and above",
        )

    def test_duplicate_color_size_combination_is_rejected(self):
        rows = [self.row("P1", "S1"), self.row("P1", "S2")]
        with self.assertRaisesRegex(ValueError, "duplicate variation combination"):
            validate_output_rows(rows, 1900)

    def test_chunks_keep_parent_products_together(self):
        rows = [
            self.row("P1", "S1", "S"),
            self.row("P1", "S2", "M"),
            self.row("P1", "S3", "L"),
            self.row("P2", "S4", "S"),
            self.row("P2", "S5", "M"),
            self.row("P2", "S6", "L"),
            self.row("P3", "S7", "S"),
            self.row("P3", "S8", "M"),
        ]
        batches = list(grouped_chunks(rows, 5))
        self.assertEqual([len(batch) for batch in batches], [3, 5])
        locations = {}
        for part, batch in enumerate(batches):
            for row in batch:
                locations.setdefault(row.parent_sku, set()).add(part)
        self.assertTrue(all(len(parts) == 1 for parts in locations.values()))


if __name__ == "__main__":
    unittest.main()
