from datetime import datetime

import pytest

from inventory_db import (
    DuplicateProductInSaleError,
    InsufficientStockError,
    InvalidValueError,
    InventoryError,
    UnknownProductError,
    adjust_stock,
    record_sale,
    restock,
)
from seed_db import COUNT_ROWS_SQL

# Seed data: product 1 (Claw Hammer) has 40 in stock, product 5 (Concrete Mix) has 5.
HAMMER = 1
CONCRETE_MIX = 5
FIXED_TIME = "2026-11-01T10:00:00"

# ------ helper functions starts -----------

def stock_of(db, product_id):
    return db.execute(
        "SELECT quantity_in_stock FROM products WHERE product_id = ?", (product_id,)
    ).fetchone()[0]


def snapshot(db):
    """Everything a failed sale must leave untouched: all row counts and all stock levels."""
    counts = [tuple(row) for row in db.execute(COUNT_ROWS_SQL)]
    stock = db.execute("SELECT product_id, quantity_in_stock FROM products").fetchall()
    return counts, [tuple(row) for row in stock]


def all_movements(db):
    return db.execute("SELECT * FROM stock_movements").fetchall()

# ------- helper function ends -------------

def test_restock_increases_stock_and_logs_one_movement(db):
    restock(db, HAMMER, 10, now=FIXED_TIME)
    assert stock_of(db, HAMMER) == 50
    movement = all_movements(db)[0]
    assert len(all_movements(db)) == 1
    assert (movement["product_id"], movement["change"]) == (HAMMER, 10)
    assert (movement["reason"], movement["occurred_at"]) == ("restock", FIXED_TIME)


@pytest.mark.parametrize("amount", [0, -5])
def test_restock_of_zero_or_less_is_refused_and_changes_nothing(db, amount):
    with pytest.raises(InvalidValueError):
        restock(db, HAMMER, amount)
    assert stock_of(db, HAMMER) == 40
    assert all_movements(db) == []


def test_restock_of_an_unknown_product_is_refused_and_logs_nothing(db):
    with pytest.raises(UnknownProductError):
        restock(db, 999, 10)
    assert all_movements(db) == []


def test_restock_without_a_time_uses_the_current_time(db):
    restock(db, HAMMER, 1)
    datetime.fromisoformat(all_movements(db)[0]["occurred_at"])  # raises if not a time


def test_adjust_can_remove_stock_and_logs_the_signed_change(db):
    adjust_stock(db, CONCRETE_MIX, -3, now=FIXED_TIME)
    assert stock_of(db, CONCRETE_MIX) == 2
    movement = all_movements(db)[0]
    assert (movement["change"], movement["reason"]) == (-3, "adjustment")
    assert movement["occurred_at"] == FIXED_TIME


def test_adjust_can_add_stock_after_a_recount(db):
    adjust_stock(db, CONCRETE_MIX, 4)
    assert stock_of(db, CONCRETE_MIX) == 9


def test_adjust_down_to_exactly_zero_is_allowed(db):
    adjust_stock(db, CONCRETE_MIX, -5)
    assert stock_of(db, CONCRETE_MIX) == 0


def test_adjust_below_zero_is_refused_and_changes_nothing(db):
    with pytest.raises(InsufficientStockError):
        adjust_stock(db, CONCRETE_MIX, -6)
    assert stock_of(db, CONCRETE_MIX) == 5
    assert all_movements(db) == []


def test_adjust_by_zero_is_refused(db):
    with pytest.raises(InvalidValueError):
        adjust_stock(db, HAMMER, 0)
    assert all_movements(db) == []


def test_adjust_of_an_unknown_product_is_refused_and_logs_nothing(db):
    with pytest.raises(UnknownProductError):
        adjust_stock(db, 999, -1)
    assert all_movements(db) == []


def test_sale_records_lines_at_current_prices_and_reduces_stock(db):
    db.execute("UPDATE products SET unit_price = 1500 WHERE product_id = ?", (HAMMER,))
    sale_id = record_sale(db, [(HAMMER, 2), (CONCRETE_MIX, 3)], now=FIXED_TIME)

    sale = db.execute("SELECT * FROM sales WHERE sale_id = ?", (sale_id,)).fetchone()
    assert sale["sold_at"] == FIXED_TIME
    lines = db.execute(
        "SELECT product_id, quantity, price_charged_per_unit FROM sale_items"
        " WHERE sale_id = ? ORDER BY product_id",
        (sale_id,),
    ).fetchall()
    assert [tuple(line) for line in lines] == [(HAMMER, 2, 1500), (CONCRETE_MIX, 3, 899)]
    assert stock_of(db, HAMMER) == 38
    assert stock_of(db, CONCRETE_MIX) == 2


def test_sale_logs_one_sale_movement_per_line(db):
    record_sale(db, [(HAMMER, 2), (CONCRETE_MIX, 3)], now=FIXED_TIME)
    movements = db.execute(
        "SELECT product_id, change, reason, occurred_at FROM stock_movements"
        " ORDER BY product_id"
    ).fetchall()
    assert [tuple(movement) for movement in movements] == [
        (HAMMER, -2, "sale", FIXED_TIME),
        (CONCRETE_MIX, -3, "sale", FIXED_TIME),
    ]


def test_sale_can_take_all_remaining_stock(db):
    record_sale(db, [(CONCRETE_MIX, 5)])
    assert stock_of(db, CONCRETE_MIX) == 0


def test_sale_that_fails_halfway_changes_nothing(db):
    before = snapshot(db)
    # The first line is fine, the second asks for more than the 5 in stock.
    with pytest.raises(InsufficientStockError):
        record_sale(db, [(HAMMER, 2), (CONCRETE_MIX, 6)])
    assert snapshot(db) == before


def test_sale_for_an_unknown_product_changes_nothing(db):
    before = snapshot(db)
    with pytest.raises(UnknownProductError):
        record_sale(db, [(HAMMER, 2), (999, 1)])
    assert snapshot(db) == before


def test_sale_with_the_same_product_twice_changes_nothing(db):
    before = snapshot(db)
    with pytest.raises(DuplicateProductInSaleError):
        record_sale(db, [(HAMMER, 1), (HAMMER, 2)])
    assert snapshot(db) == before


def test_sale_with_no_products_is_refused(db):
    before = snapshot(db)
    with pytest.raises(InvalidValueError):
        record_sale(db, [])
    assert snapshot(db) == before


@pytest.mark.parametrize("quantity", [0, -1])
def test_sale_line_with_zero_or_negative_quantity_changes_nothing(db, quantity):
    before = snapshot(db)
    with pytest.raises(InvalidValueError):
        record_sale(db, [(HAMMER, 1), (CONCRETE_MIX, quantity)])
    assert snapshot(db) == before


@pytest.mark.parametrize("error", [UnknownProductError, InsufficientStockError])
def test_stock_errors_are_inventory_errors(error):
    assert issubclass(error, InventoryError)
