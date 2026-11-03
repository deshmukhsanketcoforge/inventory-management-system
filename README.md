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
