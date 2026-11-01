## Inventory Management System

## Overview

A small hardware store keeps its stock in a spreadsheet. Prices drift, stock counts are wrong, and when a sale goes through, nobody can say exactly what changed. I build an inventroy management system for the store, from scratch.

The project uses Sqlite, Docker and Python as per the project requirements


## Database Tables and Schemas

- All tables are created with `STRICT` in `schema.sql`. 
- Every statement uses `IF NOT EXISTS`, so running the schema twice is safe. 
- Money is stored as whole cents (`INTEGER`) and shown with two decimals. (as per project requirements)
- Times are stored as ISO-8601 text. 
- Foreign key checking is turned on in `connect()` for every connection.

### 1. suppliers

Stores the companies that supply products. It is a separate table so each supplier's details are stored once and shared by many products.

| cid | name        | type    | notnull | dflt_value | pk |
|-----|-------------|---------|---------|------------|----|
| 0   | supplier_id | INTEGER | 0       |            | 1  |
| 1   | name        | TEXT    | 1       |            | 0  |

Constraints:
- `supplier_id` is the primary key.
- `name` is `NOT NULL`, `UNIQUE`, and cannot be blank, so a name search and the stock value report are never ambiguous.

### 2. products

Stores what the store sells, with its current price and stock level. This is the central table: sales and stock movements both point to it.

| cid | name              | type    | notnull | dflt_value | pk |
|-----|-------------------|---------|---------|------------|----|
| 0   | product_id        | INTEGER | 0       |            | 1  |
| 1   | sku               | TEXT    | 1       |            | 0  |
| 2   | name              | TEXT    | 1       |            | 0  |
| 3   | category          | TEXT    | 1       |            | 0  |
| 4   | supplier_id       | INTEGER | 1       |            | 0  |
| 5   | unit_price        | INTEGER | 1       |            | 0  |
| 6   | quantity_in_stock | INTEGER | 1       | 0          | 0  |
| 7   | reorder_level     | INTEGER | 1       |            | 0  |

Constraints:
- `product_id` is the primary key (the new id returned when a product is added).
- `sku` is `UNIQUE` and not blank (text such as `HT-001`).
- `name` and `category` are required and not blank.
- `supplier_id` is a foreign key to `suppliers(supplier_id)`, so an unknown supplier is refused.
- `unit_price` is in cents, with `CHECK (unit_price >= 0)`.
- `quantity_in_stock` defaults to 0, with `CHECK (quantity_in_stock >= 0)`.
- `reorder_level` is the stock count at or below which a product counts as low stock, with `CHECK (reorder_level >= 0)`.

### 3. sales

Stores one row per completed sale (the sale header). The items sold are kept in `sale_items`.

| cid | name    | type    | notnull | dflt_value | pk |
|-----|---------|---------|---------|------------|----|
| 0   | sale_id | INTEGER | 0       |            | 1  |
| 1   | sold_at | TEXT    | 1       |            | 0  |

Constraints:
- `sale_id` is the primary key.
- `sold_at` is required. The time is passed in as a parameter so tests can use a fixed date.

### 4. sale_items

Stores the lines of each sale: which product, how many, and the price charged at that moment. The price is copied here so later price changes never alter past sales.

| cid | name                   | type    | notnull | dflt_value | pk |
|-----|------------------------|---------|---------|------------|----|
| 0   | sale_id                | INTEGER | 1       |            | 1  |
| 1   | product_id             | INTEGER | 1       |            | 2  |
| 2   | quantity               | INTEGER | 1       |            | 0  |
| 3   | price_charged_per_unit | INTEGER | 1       |            | 0  |

Constraints:
- Composite primary key `(sale_id, product_id)`, so the same product cannot appear twice in one sale.
- `sale_id` is a foreign key to `sales(sale_id)`.
- `product_id` is a foreign key to `products(product_id)`. This also blocks deleting a product that has sales history.
- `quantity` has `CHECK (quantity > 0)`.
- `price_charged_per_unit` is in cents, with `CHECK (price_charged_per_unit >= 0)`.

### 5. stock_movements

Stores a log of every stock change (restock, adjustment, sale), so there is always a record of why a count changed.

| cid | name        | type    | notnull | dflt_value | pk |
|-----|-------------|---------|---------|------------|----|
| 0   | movement_id | INTEGER | 0       |            | 1  |
| 1   | product_id  | INTEGER | 1       |            | 0  |
| 2   | change      | INTEGER | 1       |            | 0  |
| 3   | reason      | TEXT    | 1       |            | 0  |
| 4   | occurred_at | TEXT    | 1       |            | 0  |

Constraints:
- `movement_id` is the primary key.
- `product_id` is a foreign key to `products(product_id)`.
- `change` is signed (negative removes stock) with `CHECK (change != 0)`.s
- `reason` has `CHECK (reason IN ('restock', 'adjustment', 'sale'))`.
- `occurred_at` is required.

### Relationships

- One supplier has many products (`products.supplier_id` → `suppliers.supplier_id`).
- One sale has many sale items (`sale_items.sale_id` → `sales.sale_id`).
- One product appears in many sale items (`sale_items.product_id` → `products.product_id`), at most once per sale.
- One product has many stock movements (`stock_movements.product_id` → `products.product_id`).

## Public Functions

### Files

- `inventory_db.py`: connection, tables and all inventory functions.
- `seed_db.py`: sample data only (`load_sample_data`, `print_row_counts`), plus a `main()` that creates the tables and seeds them.
- `main.py`: the terminal menu. It turns errors into friendly messages.

### Database setup

| Function | Inputs | Returns |
|---|---|---|
| `connect` | `db_path=None` (falls back to `INVENTORY_DB`, then a file next to the code) | A connection with foreign keys on and rows readable by column name |
| `create_tables` | `connection` | Nothing. Runs `schema.sql`|

### Products

| Function | Inputs | Returns | Errors |
|---|---|---|---|
| `add_product` | `connection, sku, name, category, supplier_id, unit_price, quantity_in_stock, reorder_level` | The new `product_id` | `DuplicateSkuError`, `UnknownSupplierError`, `InvalidValueError` (negative price or quantity) |
| `get_product` | `connection, product_id` | One row with all product columns plus `supplier_name` (joined from suppliers), or `None` | none |
| `change_product_price` | `connection, product_id, new_price` | `True` if updated, `False` if the product does not exist | `InvalidValueError` (negative price) |
| `delete_product` | `connection, product_id` | `True` if deleted, `False` if it does not exist | `ProductHasSalesError` (the product appears in `sale_items`) |

### Search

| Function | Inputs | Returns |
|---|---|---|
| `search_products` | `connection, text, category=None, max_price=None, in_stock_only=False, low_stock_only=False` | Rows sorted by name |

- `text` matches the product name, SKU or supplier name, ignoring case.
- Filters can be combined. `low_stock_only` means `quantity_in_stock <= reorder_level`.
- Every value goes in through a placeholder. Only fixed SQL fragments are joined together, so text such as `'; DROP TABLE products; --` finds nothing and changes nothing.

### Reports

Each report is a function that takes `connection` and returns rows.

| Function | Returns |
|---|---|
| `stock_value_by_supplier` | `supplier_name`, `total_value` (price × quantity), highest first |
| `low_stock_report` | Every product at or below its reorder level, with `units_short` (`reorder_level - quantity_in_stock`) |
| `sales_by_product` | `product_id`, `name`, `units_sold`, `revenue`, highest revenue first |
| `never_sold_products` | Products that appear in no sale |

### Stock changes and sales

| Function | Inputs | Returns | Errors |
|---|---|---|---|
| `restock` | `connection, product_id, amount, now=None` | Nothing | `InvalidValueError` (amount of zero or less), `UnknownProductError` |
| `adjust_stock` | `connection, product_id, change, now=None` | Nothing | `InsufficientStockError` (would make stock negative), `UnknownProductError`, `InvalidValueError` (zero) |
| `record_sale` | `connection, items, now=None`, where `items` is a list of `(product_id, quantity)` pairs | The new `sale_id` | `UnknownProductError`, `InsufficientStockError`, `DuplicateProductInSaleError`, `InvalidValueError` |
| `_change_stock` (private helper) | `connection, product_id, change, reason, now` | Nothing | Used by all three above. It updates stock and logs one movement, and never commits |

### Backup

| Function | Inputs | Returns |
|---|---|---|
| `backup_database` | `connection, backup_path` | Nothing. Copies the database with SQLite's `backup` function |

> Restore: stop the program, replace the database file with the backup copy, and run `PRAGMA integrity_check` and the row-count check on it.

### Errors

All errors inherit from `InventoryError` so the menu can catch them in one place. Each function catches the specific `sqlite3.IntegrityError` and re-raises the matching error from this list.

| Error | Raised when |
|---|---|
| `DuplicateSkuError` | The SKU already exists |
| `UnknownSupplierError` | The supplier id does not exist |
| `UnknownProductError` | The product id does not exist |
| `InvalidValueError` | A price or quantity is negative, or a restock amount is zero or less |
| `InsufficientStockError` | There is not enough stock for the sale, or an adjustment would go below zero |
| `DuplicateProductInSaleError` | The same product appears twice in one sale |
| `ProductHasSalesError` | A product with sales history is deleted |

## Transaction Steps

### restock(connection, product_id, amount, now)

1. Refuse if `amount <= 0`.
2. Increase `quantity_in_stock` for the product (the product must exist).
3. Insert a `stock_movements` row with a positive `change` and reason `restock`.

If step 3 fails, undo step 2 so that stock and the log always agree.

### adjust_stock(connection, product_id, change, now)

1. Refuse if `change == 0`.
2. Update `quantity_in_stock` by `change`. If the result would be negative, raise `InsufficientStockError`.
3. Insert a `stock_movements` row with the signed `change` and reason `adjustment`.

If step 2 is refused, nothing has been written. If step 3 fails, undo step 2.

### record_sale(connection, items, now)

1. Refuse an empty list, or the same product twice, before writing anything.
2. Insert the `sales` row with `sold_at = now`.
3. For each `(product_id, quantity)`:
   1. Read the product's current price (unknown product raises `UnknownProductError`).
   2. Insert a `sale_items` row with the current price as `price_charged_per_unit`.
   3. Call `_change_stock` with `-quantity` and reason `sale` (not enough stock raises `InsufficientStockError`).
4. Return the new `sale_id`.

If any line fails, undo the sale row, every line already inserted, every stock decrease already made, and every movement already logged. After a failed sale there is no sale row, no lines, no movements and no stock change.

## Release Plan

### Versions

| Version | Contents | Git tag | Docker image tag |
|---|---|---|---|
| 1.0.0 | Everything from pull requests 1 to 5 | `v1.0.0` | `inventory:1.0.0` |
| 1.1.0 | 1.0.0 plus a startup banner showing the number of low stock products | `v1.1.0` | `inventory:1.1.0` |

Version 1.1.0 changes no tables and no data. It only adds a read-only banner. That is why rolling back to 1.0.0 is safe.

### Releasing 1.0.0

1. Merge PR 5 and confirm CI on `main` is green.
2. Create the annotated tag: `git tag -a v1.0.0 -m "Release 1.0.0"`, then `git push origin v1.0.0`.
3. Build the image from that tagged commit: `docker build -t inventory:1.0.0 .`
4. Run the persistence check: seed or write data in one container, remove it, start a new container on the same volume, and confirm the data is still there. Paste the real output into the README.

### Releasing 1.1.0

1. Create `feature/low-stock-banner` from `main` after the `v1.0.0` tag exists.
2. The menu banner counts the rows returned by `low_stock_report` (no new query).
3. Add the 1.1.0 entry to `CHANGELOG.md`, and the README evidence (below), then merge with CI green.
4. Tag the merge commit `v1.1.0`, push it, and build `inventory:1.1.0` from that commit.

### Backup and restore

- Backup: the menu option calls `backup_database`, which uses SQLite's `Connection.backup()`. This copies a consistent snapshot even while the database is open.
- Check: open the copy and run `PRAGMA integrity_check`, which must return `ok`. Compare the row count of all five tables with the original.
- Restore: stop the program, replace the database file with the backup copy, start again, and repeat the integrity and row-count checks.
- Take a backup before every upgrade or rollback.

### Rollback from 1.1.0 to 1.0.0

1. Back up the database.
2. Stop the 1.1.0 container.
3. Start `inventory:1.0.0` with the same volume and the same `INVENTORY_DB`.
4. Confirm the data is intact: the row counts of all five tables match what they were before the rollback, and `PRAGMA integrity_check` returns `ok`.

The data survives because it lives on the volume, not in the container. The old image can read it because 1.1.0 did not change the schema. The code can also be rolled back in Git by checking out `v1.0.0`.

### Changelog

`CHANGELOG.md` has one entry per version: 1.0.0 lists the initial features, and 1.1.0 lists the low stock banner.