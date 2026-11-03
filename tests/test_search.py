import pytest

from inventory_db import add_product, search_products


def names(rows):
    return [row["name"] for row in rows]


@pytest.mark.parametrize(
    "text, expected",
    [
        ("claw", ["Claw Hammer"]),  # name
        ("CLAW", ["Claw Hammer"]),  # name, other case
        ("ht-002", ["Screwdriver Set"]),  # SKU
        ("HT-002", ["Screwdriver Set"]),  # SKU, other case
        ("garden pros", ["Garden Gloves", "Garden Hose 15m", "Pruning Shears"]),  # supplier
        ("GARDEN PROS", ["Garden Gloves", "Garden Hose 15m", "Pruning Shears"]),
    ],
)
def test_text_matches_name_sku_and_supplier_ignoring_case(db, text, expected):
    assert names(search_products(db, text)) == expected


def test_text_only_has_to_be_part_of_the_value(db):
    assert names(search_products(db, "wrench")) == ["Adjustable Wrench"]


def test_search_result_includes_the_supplier_name(db):
    row = search_products(db, "claw")[0]
    assert row["supplier_name"] == "Acme Tools Co"


def test_nothing_found_returns_an_empty_list(db):
    assert search_products(db, "no such product") == []


def test_results_are_sorted_by_name(db):
    result = names(search_products(db, ""))
    assert len(result) == 12
    assert result == sorted(result, key=str.lower)


@pytest.mark.parametrize("category", ["Electrical", "electrical", "ELECTRICAL"])
def test_category_filter_ignores_case(db, category):
    result = search_products(db, "", category=category)
    assert names(result) == ["Extension Cord 5m", "LED Bulb 4-Pack", "Work Light"]


def test_max_price_filter(db):
    result = search_products(db, "", max_price=899)
    assert names(result) == [
        "Concrete Mix 20kg",
        "Garden Gloves",
        "LED Bulb 4-Pack",
        "Wood Screws Box",
    ]


def test_in_stock_only_filter(db):
    add_product(db, "TL-001", "Out Of Stock Saw", "Hand Tools", 1, 2000, 0, 5)
    assert "Out Of Stock Saw" in names(search_products(db, "saw"))
    assert search_products(db, "saw", in_stock_only=True) == []


def test_low_stock_only_filter(db):
    result = search_products(db, "", low_stock_only=True)
    assert names(result) == [
        "Concrete Mix 20kg",
        "Extension Cord 5m",
        "Screwdriver Set",
        "Work Light",
    ]


def test_filters_combine(db):
    result = search_products(
        db, "", category="Electrical", low_stock_only=True, max_price=2000
    )
    assert names(result) == ["Extension Cord 5m"]


def test_text_and_filters_combine(db):
    result = search_products(db, "work", category="Electrical", low_stock_only=True)
    assert names(result) == ["Work Light"]


@pytest.mark.parametrize(
    "text", ["'; DROP TABLE products; --", "' OR '1'='1", "%", "_"]
)
def test_dangerous_looking_text_is_only_text(db, text):
    assert search_products(db, text) == []
    assert db.execute("SELECT COUNT(*) FROM products").fetchone()[0] == 12
