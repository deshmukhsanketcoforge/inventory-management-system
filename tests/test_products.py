import pytest

from inventory_db import (
    DuplicateSkuError,
    InvalidValueError,
    InventoryError,
    ProductHasSalesError,
    UnknownSupplierError,
    add_product,
    change_product_price,
    delete_product,
    get_product,
)

# Seed data: product 1 (Claw Hammer, Acme Tools Co) was sold, product 12 never was.
SOLD_PRODUCT = 1
NEVER_SOLD_PRODUCT = 12


def count_products(db):
    return db.execute("SELECT COUNT(*) FROM products").fetchone()[0]


def test_add_product_returns_its_new_id(db):
    product_id = add_product(db, "HT-099", "Tape Measure", "Hand Tools", 1, 799, 15, 5)
    product = get_product(db, product_id)
    assert product["sku"] == "HT-099"
    assert product["unit_price"] == 799
    assert product["quantity_in_stock"] == 15


def test_duplicate_sku_is_refused(db):
    with pytest.raises(DuplicateSkuError):
        add_product(db, "HT-001", "Another Hammer", "Hand Tools", 1, 999, 5, 2)
    assert count_products(db) == 12


def test_unknown_supplier_is_refused(db):
    with pytest.raises(UnknownSupplierError):
        add_product(db, "HT-099", "Tape Measure", "Hand Tools", 999, 799, 15, 5)
    assert count_products(db) == 12


@pytest.mark.parametrize(
    "unit_price, quantity_in_stock, reorder_level",
    [
        (-1, 10, 5),  # negative price
        (799, -1, 5),  # negative quantity
        (799, 10, -1),  # negative reorder level
    ],
)
def test_negative_price_or_quantity_is_refused(
    db, unit_price, quantity_in_stock, reorder_level
):
    with pytest.raises(InvalidValueError):
        add_product(
            db, "HT-099", "Tape Measure", "Hand Tools", 1,
            unit_price, quantity_in_stock, reorder_level,
        )  # fmt: skip
    assert count_products(db) == 12


def test_get_product_includes_the_supplier_name(db):
    product = get_product(db, SOLD_PRODUCT)
    assert product["name"] == "Claw Hammer"
    assert product["supplier_name"] == "Acme Tools Co"


def test_get_product_returns_none_for_a_missing_product(db):
    assert get_product(db, 999) is None


def test_change_price_updates_the_product(db):
    assert change_product_price(db, SOLD_PRODUCT, 1500) is True
    assert get_product(db, SOLD_PRODUCT)["unit_price"] == 1500


def test_change_price_of_a_missing_product_returns_false(db):
    assert change_product_price(db, 999, 1500) is False


def test_negative_price_is_refused_and_the_price_stays(db):
    with pytest.raises(InvalidValueError):
        change_product_price(db, SOLD_PRODUCT, -5)
    assert get_product(db, SOLD_PRODUCT)["unit_price"] == 1299


def test_a_sold_product_cannot_be_deleted(db):
    with pytest.raises(ProductHasSalesError):
        delete_product(db, SOLD_PRODUCT)
    assert get_product(db, SOLD_PRODUCT) is not None


def test_a_never_sold_product_can_be_deleted(db):
    assert delete_product(db, NEVER_SOLD_PRODUCT) is True
    assert get_product(db, NEVER_SOLD_PRODUCT) is None


def test_deleting_a_missing_product_returns_false(db):
    assert delete_product(db, 999) is False


@pytest.mark.parametrize(
    "error",
    [DuplicateSkuError, UnknownSupplierError, InvalidValueError, ProductHasSalesError],
)
def test_every_error_is_an_inventory_error(error):
    assert issubclass(error, InventoryError)
