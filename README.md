# inventory-management-system

## Database and sample data

The tables are defined in `schema.sql`. `seed_db.py` creates them and loads the sample data. The database file is `data/inventory.db` next to the code, or the path in the `INVENTORY_DB` environment variable.

```
python seed_db.py
```

Row counts printed by the seed (a second run skips the load and prints the same counts):

```
suppliers: 4
products: 12
sales: 5
sale_items: 12
stock_movements: 0
```

The sample data has 12 products in 4 categories, 3 products that were never sold, and 4 products at or below their reorder level. `stock_movements` starts empty.

## Reports

**Stock value by supplier** (`stock_value_by_supplier`), highest first:

| Supplier | Total value |
|---|---|
| BuildRight Supply | 1453.57 |
| Acme Tools Co | 1058.77 |
| Garden Pros | 829.58 |
| Spark Electric | 709.27 |

**Low stock** (`low_stock_report`), products at or below their reorder level, most units short first:

| Product | Units short |
|---|---|
| Concrete Mix 20kg | 10 |
| Screwdriver Set | 2 |
| Work Light | 2 |
| Extension Cord 5m | 0 |

**Sales by product** (`sales_by_product`), sold products only, highest revenue first:

| Product | Units sold | Revenue |
|---|---|---|
| Wood Screws Box | 30 | 194.70 |
| LED Bulb 4-Pack | 10 | 79.90 |
| Claw Hammer | 3 | 38.97 |
| Pruning Shears | 2 | 35.00 |
| Plywood Sheet | 1 | 34.99 |
| Adjustable Wrench | 2 | 30.98 |
| Concrete Mix 20kg | 3 | 26.97 |
| Garden Hose 15m | 1 | 24.99 |
| Screwdriver Set | 1 | 18.99 |

**Never sold** (`never_sold_products`), sorted by name: Extension Cord 5m, Garden Gloves, Work Light.


## Stock changes and sales

`restock`, `adjust_stock` and `record_sale` each run as one transaction (`with connection:`): every step is saved, or none is. Every change to stock also adds a row to `stock_movements` with the reason (`restock`, `adjustment` or `sale`).

### What happens when a sale fails halfway

The sale asks for 2 Claw Hammers (enough in stock) and 6 Concrete Mix (only 5 in stock). The first line is written before the second one fails, then `with connection:` rolls everything back. Real output from the sample data:

```
Before:
  sales: 5
  sale_items: 12
  stock_movements: 0
  stock of Claw Hammer (product 1): 40
  stock of Concrete Mix 20kg (product 5): 5

Call: record_sale(connection, [(1, 2), (5, 6)])
InsufficientStockError: Not enough stock of product 5 for this change.

After:
  sales: 5
  sale_items: 12
  stock_movements: 0
  stock of Claw Hammer (product 1): 40
  stock of Concrete Mix 20kg (product 5): 5
```

The row counts and both stock levels are the same before and after: no sale row, no lines, no movements and no stock change.

## The menu

Load the sample data once, then start the menu:

```
python seed_db.py
python main.py
```

The menu offers: search with filters, look up a product, add a product, restock, record a sale, the four reports, and a database backup. Money is typed and shown with two decimals (`12.99`). A problem (a broken rule, a missing product, letters where a number is expected) prints a message starting with `Error:` and returns to the menu. Press `0` to quit.

## Backup and restore

**Back up.** Choose option 10 in the menu and type a file name (or press Enter for `backup.db`). The copy is made with SQLite's backup function, so it is a consistent snapshot even while the database is in use.

**Check the copy.** It must pass `PRAGMA integrity_check` and have the same row counts as the original. Real output, after backing up the freshly seeded database to `data/backup.db`:

```
python - <<'EOF'
from contextlib import closing
from inventory_db import connect
from seed_db import COUNT_ROWS_SQL
for path in ("data/inventory.db", "data/backup.db"):
    with closing(connect(path)) as connection:
        print(path)
        print("  integrity_check:", connection.execute("PRAGMA integrity_check").fetchone()[0])
        for table, count in connection.execute(COUNT_ROWS_SQL):
            print(f"  {table}: {count}")
EOF
```

```
data/inventory.db
  integrity_check: ok
  suppliers: 4
  products: 12
  sales: 5
  sale_items: 12
  stock_movements: 0
data/backup.db
  integrity_check: ok
  suppliers: 4
  products: 12
  sales: 5
  sale_items: 12
  stock_movements: 0
```

**Restore.** Stop the program, replace the database file with the backup copy, then start again and run the check above on the restored file:

```
cp data/backup.db data/inventory.db
```
