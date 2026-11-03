from inventory_db import (
    add_product,
    low_stock_report,
    never_sold_products,
    sales_by_product,
    stock_value_by_supplier,
)


def test_stock_value_by_supplier_is_highest_first(db):
    rows = stock_value_by_supplier(db)
    assert [(row["supplier_name"], row["total_value"]) for row in rows] == [
        ("BuildRight Supply", 145357),
        ("Acme Tools Co", 105877),
        ("Garden Pros", 82958),
        ("Spark Electric", 70927),
    ]


def test_stock_value_includes_a_supplier_with_no_products(empty_db):
    empty_db.execute("INSERT INTO suppliers (name) VALUES ('New Supplier')")
    rows = stock_value_by_supplier(empty_db)
    assert [(row["supplier_name"], row["total_value"]) for row in rows] == [("New Supplier", 0)]


def test_low_stock_report_lists_products_with_units_short(db):
    rows = low_stock_report(db)
    assert [(row["name"], row["units_short"]) for row in rows] == [
        ("Concrete Mix 20kg", 10),
        ("Screwdriver Set", 2),
        ("Work Light", 2),
        ("Extension Cord 5m", 0),
    ]


def test_low_stock_report_includes_a_product_exactly_at_its_level(db):
    names = [row["name"] for row in low_stock_report(db)]
    assert "Extension Cord 5m" in names  # 10 in stock, reorder level 10


def test_low_stock_report_leaves_out_well_stocked_products(db):
    names = [row["name"] for row in low_stock_report(db)]
    assert "Claw Hammer" not in names
    add_product(db, "HT-099", "Tape Measure", "Hand Tools", 1, 799, 15, 5)
    assert "Tape Measure" not in [row["name"] for row in low_stock_report(db)]


def test_sales_by_product_has_units_and_revenue_highest_first(db):
    rows = sales_by_product(db)
    assert [(row["name"], row["units_sold"], row["revenue"]) for row in rows] == [
        ("Wood Screws Box", 30, 19470),
        ("LED Bulb 4-Pack", 10, 7990),
        ("Claw Hammer", 3, 3897),
        ("Pruning Shears", 2, 3500),
        ("Plywood Sheet", 1, 3499),
        ("Adjustable Wrench", 2, 3098),
        ("Concrete Mix 20kg", 3, 2697),
        ("Garden Hose 15m", 1, 2499),
        ("Screwdriver Set", 1, 1899),
    ]


def test_sales_by_product_uses_the_price_charged_at_the_time(db):
    db.execute("UPDATE products SET unit_price = 5000 WHERE name = 'Claw Hammer'")
    hammer = next(row for row in sales_by_product(db) if row["name"] == "Claw Hammer")
    assert hammer["revenue"] == 3897


def test_sales_by_product_is_empty_when_nothing_was_sold(empty_db):
    assert sales_by_product(empty_db) == []


def test_never_sold_products_lists_products_in_no_sale(db):
    rows = never_sold_products(db)
    assert [row["name"] for row in rows] == ["Extension Cord 5m", "Garden Gloves", "Work Light"]


def test_a_product_leaves_the_never_sold_report_once_it_is_sold(db):
    db.execute("INSERT INTO sale_items VALUES (1, 12, 1, 599)")
    names = [row["name"] for row in never_sold_products(db)]
    assert "Garden Gloves" not in names
