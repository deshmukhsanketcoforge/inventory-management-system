import os
import sqlite3
from datetime import datetime
from pathlib import Path

CODE_DIR = Path(__file__).parent
SCHEMA_PATH = CODE_DIR / "schema.sql"
DEFAULT_DB = str(CODE_DIR / "data" / "inventory.db")


class InventoryError(Exception):
    """Base class, so the menu can catch every inventory problem in one place."""


class DuplicateSkuError(InventoryError):
    pass


class UnknownSupplierError(InventoryError):
    pass


class InvalidValueError(InventoryError):
    pass


class ProductHasSalesError(InventoryError):
    pass


class UnknownProductError(InventoryError):
    pass


class InsufficientStockError(InventoryError):
    pass


class DuplicateProductInSaleError(InventoryError):
    pass


def get_db_path(environ=os.environ):
    """Database file from INVENTORY_DB, or data/inventory.db next to the code."""
    return environ.get("INVENTORY_DB", DEFAULT_DB)


def connect(db_path=None):
    """Open the database with foreign keys on and rows readable by column name."""
    if db_path is None:
        db_path = get_db_path()
    if db_path != ":memory:":
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)  # e.g. data/ on first run
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def create_tables(connection):
    """Run schema.sql. Safe to call again, existing tables and data are kept."""
    connection.executescript(SCHEMA_PATH.read_text())


def _raise_product_error(error):
    """Turn the database's IntegrityError into the matching inventory error."""
    message = str(error)
    if "UNIQUE" in message:
        raise DuplicateSkuError("A product with this SKU already exists.") from error
    if "FOREIGN KEY" in message:
        raise UnknownSupplierError("That supplier does not exist.") from error
    if "CHECK" in message:
        raise InvalidValueError(
            "Price, quantity and reorder level cannot be negative, "
            "and SKU, name and category cannot be blank."
        ) from error
    raise error


def add_product(
    connection, sku, name, category, supplier_id, unit_price, quantity_in_stock, reorder_level
):
    """Add a product and return its new product_id. Prices are in cents."""
    try:
        with connection:
            cursor = connection.execute(
                "INSERT INTO products (sku, name, category, supplier_id, unit_price,"
                " quantity_in_stock, reorder_level) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (sku, name, category, supplier_id, unit_price, quantity_in_stock, reorder_level),
            )
    except sqlite3.IntegrityError as error:
        _raise_product_error(error)
    return cursor.lastrowid


def get_product(connection, product_id):
    """One product with its supplier_name, or None if there is no such product."""
    return connection.execute(
        "SELECT products.*, suppliers.name AS supplier_name"
        " FROM products JOIN suppliers ON suppliers.supplier_id = products.supplier_id"
        " WHERE products.product_id = ?",
        (product_id,),
    ).fetchone()


def change_product_price(connection, product_id, new_price):
    """Set a new price in cents. Returns False if the product does not exist."""
    try:
        with connection:
            cursor = connection.execute(
                "UPDATE products SET unit_price = ? WHERE product_id = ?",
                (new_price, product_id),
            )
    except sqlite3.IntegrityError as error:
        _raise_product_error(error)
    return cursor.rowcount == 1


def delete_product(connection, product_id):
    """Delete a product. Returns False if it does not exist."""
    try:
        with connection:
            cursor = connection.execute(
                "DELETE FROM products WHERE product_id = ?", (product_id,)
            )
    except sqlite3.IntegrityError as error:
        raise ProductHasSalesError(
            "This product has sales history and cannot be deleted."
        ) from error
    return cursor.rowcount == 1


def search_products(
    connection, text, category=None, max_price=None, in_stock_only=False, low_stock_only=False
):
    """Products whose name, SKU or supplier name contains text, ignoring case.

    category also ignores case. max_price is in cents. The filters can be
    combined. Sorted by name.
    """
    # Only fixed pieces of SQL are joined here, every value goes in as a ?
    conditions = [
        (
            "(instr(lower(products.name), lower(?)) > 0"
            " OR instr(lower(products.sku), lower(?)) > 0"
            " OR instr(lower(suppliers.name), lower(?)) > 0)"
        )
    ]
    values = [text, text, text]
    if category is not None:
        conditions.append("lower(products.category) = lower(?)")
        values.append(category)
    if max_price is not None:
        conditions.append("products.unit_price <= ?")
        values.append(max_price)
    if in_stock_only:
        conditions.append("products.quantity_in_stock > 0")
    if low_stock_only:
        conditions.append("products.quantity_in_stock <= products.reorder_level")
    return connection.execute(
        "SELECT products.*, suppliers.name AS supplier_name"
        " FROM products JOIN suppliers ON suppliers.supplier_id = products.supplier_id"
        " WHERE " + " AND ".join(conditions) + " ORDER BY products.name COLLATE NOCASE",
        values,
    ).fetchall()


def stock_value_by_supplier(connection):
    """Each supplier with the total value of its stock in cents, highest first."""
    return connection.execute(
        "SELECT suppliers.name AS supplier_name,"
        " COALESCE(SUM(products.unit_price * products.quantity_in_stock), 0) AS total_value"
        " FROM suppliers LEFT JOIN products ON products.supplier_id = suppliers.supplier_id"
        " GROUP BY suppliers.supplier_id"
        " ORDER BY total_value DESC, suppliers.name"
    ).fetchall()


def low_stock_report(connection):
    """Products at or below their reorder level, with how many units short they are."""
    return connection.execute(
        "SELECT product_id, name, quantity_in_stock, reorder_level,"
        " reorder_level - quantity_in_stock AS units_short"
        " FROM products WHERE quantity_in_stock <= reorder_level"
        " ORDER BY units_short DESC, name"
    ).fetchall()


def sales_by_product(connection):
    """Each sold product with the units sold and revenue in cents, highest revenue first."""
    return connection.execute(
        "SELECT products.product_id, products.name,"
        " SUM(sale_items.quantity) AS units_sold,"
        " SUM(sale_items.quantity * sale_items.price_charged_per_unit) AS revenue"
        " FROM sale_items JOIN products ON products.product_id = sale_items.product_id"
        " GROUP BY products.product_id"
        " ORDER BY revenue DESC, products.name"
    ).fetchall()


def never_sold_products(connection):
    """Products that appear in no sale, sorted by name."""
    return connection.execute(
        "SELECT product_id, sku, name, category, quantity_in_stock FROM products"
        " WHERE product_id NOT IN (SELECT product_id FROM sale_items)"
        " ORDER BY name"
    ).fetchall()


def _change_stock(connection, product_id, change, reason, now):
    """Change a product's stock and log the movement. Never commits (because of complete transaction behavior)

    So a failure here undoes the stock change and the log row together.
    """
    try:
        cursor = connection.execute(
            "UPDATE products SET quantity_in_stock = quantity_in_stock + ?"
            " WHERE product_id = ?",
            (change, product_id),
        )
    except sqlite3.IntegrityError as error:
        # The only rule an update can break is stock going below zero.
        raise InsufficientStockError("Not enough stock for this change.") from error
    if cursor.rowcount == 0:
        raise UnknownProductError("That product does not exist.")
    connection.execute(
        "INSERT INTO stock_movements (product_id, change, reason, occurred_at)"
        " VALUES (?, ?, ?, ?)",
        (product_id, change, reason, now),
    )


def _current_time(now):
    """The time given by the caller, or the current time when none was given."""
    return now if now is not None else datetime.now().isoformat(timespec="seconds")


def restock(connection, product_id, amount, now=None):
    """Add amount (more than zero) to a product's stock and log a restock movement."""
    if amount <= 0:
        raise InvalidValueError("A restock amount must be more than zero.")
    with connection:
        _change_stock(connection, product_id, amount, "restock", _current_time(now))


def adjust_stock(connection, product_id, change, now=None):
    """Change stock by a signed amount (damage, recount) and log an adjustment movement."""
    if change == 0:
        raise InvalidValueError("An adjustment cannot be zero.")
    with connection:
        _change_stock(connection, product_id, change, "adjustment", _current_time(now))
