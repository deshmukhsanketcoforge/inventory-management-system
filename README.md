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
