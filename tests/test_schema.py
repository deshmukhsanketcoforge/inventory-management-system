import sqlite3

import pytest

from inventory_db import create_tables

TABLES = {"suppliers", "products", "sales", "sale_items", "stock_movements"}

# -------- Helper Function Starts -----------------

def add_supplier(db, name="Acme"):
    return db.execute("INSERT INTO suppliers (name) VALUES (?)", (name,)).lastrowid


def add_product(db, supplier_id, **overrides):
    """Insert a valid product, with any column replaced by the caller."""
    values = {
        "sku": "HT-001",
        "name": "Hammer",
        "category": "Tools",
        "supplier_id": supplier_id,
        "unit_price": 1299,
        "quantity_in_stock": 10,
        "reorder_level": 5,
    }
    values.update(overrides)
    return db.execute(
        "INSERT INTO products (sku, name, category, supplier_id, unit_price,"
        " quantity_in_stock, reorder_level) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            values["sku"],
            values["name"],
            values["category"],
            values["supplier_id"],
            values["unit_price"],
            values["quantity_in_stock"],
            values["reorder_level"],
        ),
    ).lastrowid


def add_sale(db):
    return db.execute(
        "INSERT INTO sales (sold_at) VALUES (?)", ("2026-01-01T10:00:00",)
    ).lastrowid

# -------- Helper Function Ends -----------------

def test_all_five_tables_exist(empty_db):
    rows = empty_db.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table'"
    ).fetchall()
    assert TABLES <= {row["name"] for row in rows}


def test_all_tables_are_strict(empty_db):
    rows = empty_db.execute("PRAGMA table_list").fetchall()
    strict = {row["name"]: row["strict"] for row in rows}
    assert all(strict[table] == 1 for table in TABLES)


def test_running_the_schema_twice_keeps_data(empty_db):
    add_supplier(empty_db)
    create_tables(empty_db)
    count = empty_db.execute("SELECT COUNT(*) FROM suppliers").fetchone()[0]
    assert count == 1


def test_supplier_names_must_be_unique(empty_db):
    add_supplier(empty_db, "Acme")
    with pytest.raises(sqlite3.IntegrityError):
        add_supplier(empty_db, "Acme")


def test_sku_must_be_unique(empty_db):
    supplier_id = add_supplier(empty_db)
    add_product(empty_db, supplier_id)
    with pytest.raises(sqlite3.IntegrityError):
        add_product(empty_db, supplier_id, name="Another hammer")


@pytest.mark.parametrize(
    "bad_value",
    [
        {"sku": None},
        {"sku": ""},
        {"name": "  "},
        {"category": ""},
        {"unit_price": -1},
        {"quantity_in_stock": -1},
        {"reorder_level": -1},
    ],
)
def test_products_refuse_missing_blank_or_negative_values(empty_db, bad_value):
    supplier_id = add_supplier(empty_db)
    with pytest.raises(sqlite3.IntegrityError):
        add_product(empty_db, supplier_id, **bad_value)


def test_quantity_in_stock_defaults_to_zero(empty_db):
    supplier_id = add_supplier(empty_db)
    empty_db.execute(
        "INSERT INTO products (sku, name, category, supplier_id, unit_price,"
        " reorder_level) VALUES ('X-1', 'Nails', 'Tools', ?, 100, 5)",
        (supplier_id,),
    )
    row = empty_db.execute("SELECT quantity_in_stock FROM products").fetchone()
    assert row["quantity_in_stock"] == 0


def test_product_needs_an_existing_supplier(empty_db):
    with pytest.raises(sqlite3.IntegrityError):
        add_product(empty_db, supplier_id=999)


def test_sale_item_needs_an_existing_sale_and_product(empty_db):
    sale_id = add_sale(empty_db)
    with pytest.raises(sqlite3.IntegrityError):
        empty_db.execute(
            "INSERT INTO sale_items VALUES (?, 999, 1, 100)", (sale_id,)
        )


@pytest.mark.parametrize("quantity, price", [(0, 100), (-1, 100), (1, -100)])
def test_sale_items_refuse_bad_quantity_or_price(empty_db, quantity, price):
    product_id = add_product(empty_db, add_supplier(empty_db))
    sale_id = add_sale(empty_db)
    with pytest.raises(sqlite3.IntegrityError):
        empty_db.execute(
            "INSERT INTO sale_items VALUES (?, ?, ?, ?)",
            (sale_id, product_id, quantity, price),
        )


def test_same_product_cannot_appear_twice_in_one_sale(empty_db):
    product_id = add_product(empty_db, add_supplier(empty_db))
    sale_id = add_sale(empty_db)
    line = (sale_id, product_id, 1, 100)
    empty_db.execute("INSERT INTO sale_items VALUES (?, ?, ?, ?)", line)
    with pytest.raises(sqlite3.IntegrityError):
        empty_db.execute("INSERT INTO sale_items VALUES (?, ?, ?, ?)", line)


def test_a_product_with_sales_cannot_be_deleted(empty_db):
    product_id = add_product(empty_db, add_supplier(empty_db))
    sale_id = add_sale(empty_db)
    empty_db.execute(
        "INSERT INTO sale_items VALUES (?, ?, 1, 100)", (sale_id, product_id)
    )
    with pytest.raises(sqlite3.IntegrityError):
        empty_db.execute("DELETE FROM products WHERE product_id = ?", (product_id,))


@pytest.mark.parametrize(
    "product_id, change, reason",
    [
        (1, 5, "restock"),
        (1, -2, "adjustment"),
        (1, -1, "sale"),
    ],
)
def test_stock_movement_accepts_the_three_reasons(empty_db, product_id, change, reason):
    add_product(empty_db, add_supplier(empty_db))
    empty_db.execute(
        "INSERT INTO stock_movements (product_id, change, reason, occurred_at)"
        " VALUES (?, ?, ?, '2026-01-01T10:00:00')",
        (product_id, change, reason),
    )
    assert empty_db.execute("SELECT COUNT(*) FROM stock_movements").fetchone()[0] == 1


@pytest.mark.parametrize(
    "product_id, change, reason",
    [
        (1, 5, "theft"),   # reason not in the allowed list
        (1, 0, "restock"),  # a movement must change something
        (999, 5, "restock"),  # unknown product
    ],
)
def test_stock_movement_refuses_bad_rows(empty_db, product_id, change, reason):
    add_product(empty_db, add_supplier(empty_db))
    with pytest.raises(sqlite3.IntegrityError):
        empty_db.execute(
            "INSERT INTO stock_movements (product_id, change, reason, occurred_at)"
            " VALUES (?, ?, ?, '2026-01-01T10:00:00')",
            (product_id, change, reason),
        )


def test_indexes_exist_for_the_joins(empty_db):
    rows = empty_db.execute(
        "SELECT name FROM sqlite_master WHERE type = 'index'"
    ).fetchall()
    names = {row["name"] for row in rows}
    assert {"idx_products_supplier", "idx_sale_items_product"} <= names
