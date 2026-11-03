"""Terminal menu for the inventory database."""

import sqlite3
from contextlib import closing

from inventory_db import (
    InventoryError,
    add_product,
    backup_database,
    connect,
    create_tables,
    get_product,
    low_stock_report,
    never_sold_products,
    record_sale,
    restock,
    sales_by_product,
    search_products,
    stock_value_by_supplier,
)

PRODUCT_HEADERS = ["ID", "SKU", "Name", "Category", "Supplier", "Price", "In stock", "Reorder at"]


class InputError(Exception):
    """Text typed by the user that cannot be used, e.g. letters where a number is expected."""


def format_money(cents):
    """Whole cents as text with two decimals: 1299 -> '12.99'."""
    dollars, rest = divmod(cents, 100)
    return f"{dollars}.{rest:02d}"


def parse_whole_number(text):
    """Text as a whole number, or InputError with a friendly message."""
    try:
        return int(text)
    except ValueError:
        raise InputError(f"'{text}' is not a whole number.") from None


def parse_money(text):
    """A price like '12.99' as whole cents, or InputError with a friendly message."""
    try:
        return round(float(text) * 100)
    except (ValueError, OverflowError):  # letters, 'nan' or 'inf'
        raise InputError(f"'{text}' is not a price like 12.99.") from None


def ask_text(prompt):
    return input(prompt).strip()


def ask_whole_number(prompt):
    return parse_whole_number(ask_text(prompt))


def ask_money(prompt):
    return parse_money(ask_text(prompt))


def ask_optional_money(prompt):
    """A price, or None when the answer is left blank."""
    text = ask_text(prompt)
    return parse_money(text) if text else None


def ask_yes_no(prompt):
    return ask_text(prompt).lower() in ("y", "yes")


def print_table(headers, rows):
    """Print the headers, then one line per row."""
    if not rows:
        print("Nothing found.")
        return
    print(" | ".join(headers))
    for row in rows:
        print(" | ".join(str(value) for value in row))


def product_cells(product):
    return [
        product["product_id"],
        product["sku"],
        product["name"],
        product["category"],
        product["supplier_name"],
        format_money(product["unit_price"]),
        product["quantity_in_stock"],
        product["reorder_level"],
    ]


def search_action(connection):
    text = ask_text("Search text (name, SKU or supplier, blank for all): ")
    category = ask_text("Category (blank for any): ") or None
    max_price = ask_optional_money("Highest price (blank for any): ")
    in_stock_only = ask_yes_no("Only products in stock? (y/n): ")
    low_stock_only = ask_yes_no("Only low stock products? (y/n): ")
    products = search_products(connection, text, category, max_price, in_stock_only, low_stock_only)
    print_table(PRODUCT_HEADERS, [product_cells(product) for product in products])


def look_up_action(connection):
    product_id = ask_whole_number("Product id: ")
    product = get_product(connection, product_id)
    if product is None:
        print(f"No product with id {product_id}.")
    else:
        print_table(PRODUCT_HEADERS, [product_cells(product)])


def add_product_action(connection):
    sku = ask_text("SKU: ")
    name = ask_text("Name: ")
    category = ask_text("Category: ")
    supplier_id = ask_whole_number("Supplier id: ")
    unit_price = ask_money("Price (e.g. 12.99): ")
    quantity = ask_whole_number("Quantity in stock: ")
    reorder_level = ask_whole_number("Reorder level: ")
    product_id = add_product(
        connection, sku, name, category, supplier_id, unit_price, quantity, reorder_level
    )
    print(f"Added product {product_id}.")


def restock_action(connection):
    product_id = ask_whole_number("Product id: ")
    amount = ask_whole_number("Amount to add: ")
    restock(connection, product_id, amount)
    product = get_product(connection, product_id)
    print(f"Restocked. {product['name']} now has {product['quantity_in_stock']} in stock.")


def record_sale_action(connection):
    items = []
    while True:
        text = ask_text("Product id (blank when the sale is complete): ")
        if not text:
            break
        items.append((parse_whole_number(text), ask_whole_number("Quantity: ")))
    sale_id = record_sale(connection, items)
    print(f"Sale {sale_id} recorded.")


def stock_value_action(connection):
    rows = [
        [row["supplier_name"], format_money(row["total_value"])]
        for row in stock_value_by_supplier(connection)
    ]
    print_table(["Supplier", "Total value"], rows)


def low_stock_action(connection):
    rows = [
        [row["product_id"], row["name"], row["quantity_in_stock"], row["reorder_level"],
         row["units_short"]]
        for row in low_stock_report(connection)
    ]
    print_table(["ID", "Name", "In stock", "Reorder at", "Units short"], rows)


def sales_by_product_action(connection):
    rows = [
        [row["product_id"], row["name"], row["units_sold"], format_money(row["revenue"])]
        for row in sales_by_product(connection)
    ]
    print_table(["ID", "Name", "Units sold", "Revenue"], rows)


def never_sold_action(connection):
    rows = [
        [row["product_id"], row["sku"], row["name"], row["category"], row["quantity_in_stock"]]
        for row in never_sold_products(connection)
    ]
    print_table(["ID", "SKU", "Name", "Category", "In stock"], rows)


def backup_action(connection):
    backup_path = ask_text("Backup file name [backup.db]: ") or "backup.db"
    backup_database(connection, backup_path)
    print(f"Backup saved to {backup_path}.")


# (menu number, text shown, function that does it)
MENU = [
    ("1", "Search products", search_action),
    ("2", "Look up a product", look_up_action),
    ("3", "Add a product", add_product_action),
    ("4", "Restock a product", restock_action),
    ("5", "Record a sale", record_sale_action),
    ("6", "Report: stock value by supplier", stock_value_action),
    ("7", "Report: low stock", low_stock_action),
    ("8", "Report: sales by product", sales_by_product_action),
    ("9", "Report: never sold", never_sold_action),
    ("10", "Back up the database", backup_action),
]
ACTIONS = {number: action for number, _, action in MENU}


def print_menu():
    print("\nInventory menu")
    for number, text, _ in MENU:
        print(f"  {number}. {text}")
    print("  0. Quit")


def run_menu(connection):
    """Show the menu until the user quits. Problems are printed, never raised."""
    while True:
        print_menu()
        choice = ask_text("Choose an option: ")
        if choice == "0":
            return
        action = ACTIONS.get(choice)
        if action is None:
            print("Please type a number from the menu.")
            continue
        try:
            action(connection)
        except (InventoryError, InputError) as error:
            print(f"Error: {error}")
        except sqlite3.Error as error:
            print(f"Database error: {error}")


def main():
    with closing(connect()) as connection:
        create_tables(connection)
        run_menu(connection)


if __name__ == "__main__":
    main()
