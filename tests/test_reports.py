from inventory_db import add_product, low_stock_report, stock_value_by_supplier


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
