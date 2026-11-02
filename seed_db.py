from contextlib import closing

from inventory_db import connect, create_tables

SUPPLIERS = [
    ("Acme Tools Co",),
    ("BuildRight Supply",),
    ("Garden Pros",),
    ("Spark Electric",),
]

# sku, name, category, supplier_id, unit_price (cents), quantity_in_stock, reorder_level
PRODUCTS = [
    ("HT-001", "Claw Hammer", "Hand Tools", 1, 1299, 40, 10),
    ("HT-002", "Screwdriver Set", "Hand Tools", 1, 1899, 8, 10),
    ("HT-003", "Adjustable Wrench", "Hand Tools", 1, 1549, 25, 8),
    ("BM-001", "Wood Screws Box", "Building Materials", 2, 649, 120, 50),
    ("BM-002", "Concrete Mix 20kg", "Building Materials", 2, 899, 5, 15),
    ("BM-003", "Plywood Sheet", "Building Materials", 2, 3499, 18, 6),
    ("GD-001", "Garden Hose 15m", "Garden", 3, 2499, 12, 5),
    ("GD-002", "Pruning Shears", "Garden", 3, 1750, 20, 6),
    ("EL-001", "LED Bulb 4-Pack", "Electrical", 4, 799, 60, 20),
    ("EL-002", "Extension Cord 5m", "Electrical", 4, 1399, 10, 10),
    ("EL-003", "Work Light", "Electrical", 4, 2999, 3, 5),
    ("GD-003", "Garden Gloves", "Garden", 3, 599, 30, 10),
]

SALES = [
    ("2026-10-01T09:15:00",),
    ("2026-10-02T11:30:00",),
    ("2026-10-03T14:05:00",),
    ("2026-10-04T16:45:00",),
    ("2026-10-05T10:20:00",),
]

# sale_id, product_id, quantity, price_charged_per_unit (cents, the price at the time)
SALE_ITEMS = [
    (1, 1, 2, 1299),
    (1, 4, 10, 649),
    (1, 9, 4, 799),
    (2, 2, 1, 1899),
    (2, 7, 1, 2499),
    (3, 3, 2, 1549),
    (3, 5, 3, 899),
    (3, 6, 1, 3499),
    (4, 8, 2, 1750),
    (4, 4, 20, 649),
    (5, 9, 6, 799),
    (5, 1, 1, 1299),
]

HAS_DATA_SQL = "SELECT EXISTS (SELECT 1 FROM suppliers)"

COUNT_ROWS_SQL = """
    SELECT 'suppliers', COUNT(*) FROM suppliers
    UNION ALL SELECT 'products', COUNT(*) FROM products
    UNION ALL SELECT 'sales', COUNT(*) FROM sales
    UNION ALL SELECT 'sale_items', COUNT(*) FROM sale_items
    UNION ALL SELECT 'stock_movements', COUNT(*) FROM stock_movements
"""


def load_sample_data(connection):
    """Fill the tables with sample data. stock_movements is left empty."""
    with connection:
        connection.executemany("INSERT INTO suppliers (name) VALUES (?)", SUPPLIERS)
        connection.executemany(
            "INSERT INTO products (sku, name, category, supplier_id, unit_price,"
            " quantity_in_stock, reorder_level) VALUES (?, ?, ?, ?, ?, ?, ?)",
            PRODUCTS,
        )
        connection.executemany("INSERT INTO sales (sold_at) VALUES (?)", SALES)
        connection.executemany(
            "INSERT INTO sale_items (sale_id, product_id, quantity,"
            " price_charged_per_unit) VALUES (?, ?, ?, ?)",
            SALE_ITEMS,
        )


def print_row_counts(connection):
    for table, count in connection.execute(COUNT_ROWS_SQL):
        print(f"{table}: {count}")


def main():
    with closing(connect()) as connection:
        create_tables(connection)
        # Skip the load when data is already there, e.g. on a reused Docker volume
        if connection.execute(HAS_DATA_SQL).fetchone()[0]:
            print("Database already has data, skipping sample data.")
        else:
            load_sample_data(connection)
        print_row_counts(connection)


if __name__ == "__main__":
    main()
