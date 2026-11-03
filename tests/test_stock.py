from datetime import datetime

import pytest

from inventory_db import (
    InsufficientStockError,
    InvalidValueError,
    InventoryError,
    UnknownProductError,
    adjust_stock,
    restock,
)

# Seed data: product 1 (Claw Hammer) has 40 in stock, product 5 (Concrete Mix) has 5.
HAMMER = 1
CONCRETE_MIX = 5
FIXED_TIME = "2026-11-01T10:00:00"

# ------ helper functions starts -----------

def stock_of(db, product_id):
    return db.execute(
        "SELECT quantity_in_stock FROM products WHERE product_id = ?", (product_id,)
    ).fetchone()[0]


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


@pytest.mark.parametrize("error", [UnknownProductError, InsufficientStockError])
def test_stock_errors_are_inventory_errors(error):
    assert issubclass(error, InventoryError)
