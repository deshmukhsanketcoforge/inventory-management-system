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

The menu offers: search with filters, look up a product, add a product, restock, record a sale, the four reports, and a database backup. Money is typed and shown with two decimals (`12.99`). A problem (a broken rule, a missing product, letters where a number is expected) prints a message starting with `Error:` and returns to the menu. When the menu starts it shows a banner with the number of low stock products (at or below their reorder level). Press `0` to quit.

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


## Docker

The image uses a pinned Python version (`python:3.12.16-slim`). The database lives in `/data` inside the container, set by the `INVENTORY_DB` environment variable. When `INVENTORY_DB` is not set (outside Docker), the database is `data/inventory.db` next to the code.

**Build** the image. Real output of `docker build --no-cache --progress=plain -t inventory:dev .`:

```
#0 building with "desktop-linux" instance using docker driver

#1 [internal] load build definition from Dockerfile
#1 transferring dockerfile: 513B done
#1 DONE 0.0s

#2 [internal] load metadata for docker.io/library/python:3.12.16-slim
#2 DONE 0.3s

#3 [internal] load .dockerignore
#3 transferring context: 149B done
#3 DONE 0.0s

#4 [1/6] FROM docker.io/library/python:3.12.16-slim@sha256:b18b261e1b4974b4f321451ad5251ded85abb22c2b8b262da527dda1d031ab30
#4 resolve docker.io/library/python:3.12.16-slim@sha256:b18b261e1b4974b4f321451ad5251ded85abb22c2b8b262da527dda1d031ab30 0.0s done
#4 DONE 0.0s

#5 [2/6] WORKDIR /app
#5 CACHED

#6 [internal] load build context
#6 transferring context: 1.50kB done
#6 DONE 0.0s

#7 [3/6] COPY requirements.txt .
#7 DONE 0.0s

#8 [4/6] RUN pip install --no-cache-dir -r requirements.txt
#8 0.636 Collecting iniconfig==2.3.1 (from -r requirements.txt (line 1))
#8 0.686   Downloading iniconfig-2.3.1-py3-none-any.whl.metadata (2.8 kB)
#8 0.721 Collecting packaging==26.3 (from -r requirements.txt (line 2))
#8 0.730   Downloading packaging-26.3-py3-none-any.whl.metadata (3.5 kB)
#8 0.760 Collecting pluggy==1.7.0 (from -r requirements.txt (line 3))
#8 0.769   Downloading pluggy-1.7.0-py3-none-any.whl.metadata (5.0 kB)
#8 0.811 Collecting Pygments==2.21.0 (from -r requirements.txt (line 4))
#8 0.820   Downloading pygments-2.21.0-py3-none-any.whl.metadata (2.5 kB)
#8 0.874 Collecting pytest==9.2.0 (from -r requirements.txt (line 5))
#8 0.883   Downloading pytest-9.2.0-py3-none-any.whl.metadata (7.9 kB)
#8 1.110 Collecting ruff==0.17.3 (from -r requirements.txt (line 6))
#8 1.122   Downloading ruff-0.17.3-py3-none-manylinux_2_17_aarch64.manylinux2014_aarch64.whl.metadata (20 kB)
#8 1.135 Downloading iniconfig-2.3.1-py3-none-any.whl (7.6 kB)
#8 1.145 Downloading packaging-26.3-py3-none-any.whl (129 kB)
#8 1.174 Downloading pluggy-1.7.0-py3-none-any.whl (27 kB)
#8 1.183 Downloading pygments-2.21.0-py3-none-any.whl (1.3 MB)
#8 1.301    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 1.3/1.3 MB 9.3 MB/s eta 0:00:00
#8 1.311 Downloading pytest-9.2.0-py3-none-any.whl (411 kB)
#8 1.343 Downloading ruff-0.17.3-py3-none-manylinux_2_17_aarch64.manylinux2014_aarch64.whl (10.1 MB)
#8 1.508    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 10.1/10.1 MB 61.9 MB/s eta 0:00:00
#8 1.541 Installing collected packages: ruff, Pygments, pluggy, packaging, iniconfig, pytest
#8 1.995 Successfully installed Pygments-2.21.0 iniconfig-2.3.1 packaging-26.3 pluggy-1.7.0 pytest-9.2.0 ruff-0.17.3
#8 1.995 WARNING: Running pip as the 'root' user can result in broken permissions and conflicting behaviour with the system package manager, possibly rendering your system unusable. It is recommended to use a virtual environment instead: https://pip.pypa.io/warnings/venv. Use the --root-user-action option if you know what you are doing and want to suppress this warning.
#8 2.111 
#8 2.111 [notice] A new release of pip is available: 25.0.1 -> 26.3
#8 2.111 [notice] To update, run: pip install --upgrade pip
#8 DONE 2.2s

#9 [5/6] COPY . .
#9 DONE 0.0s

#10 [6/6] RUN mkdir -p /data
#10 DONE 0.1s

#11 exporting to image
#11 exporting layers
#11 exporting layers 0.7s done
#11 exporting manifest sha256:d9f33bb72426fd2fd623e3ed97443aa717869669125998f65bdb5a1048fcb7eb done
#11 exporting config sha256:87253d2b263a547ec4b5e430e987a7a7117b5af9a28ac90da8f3f6148f324acd done
#11 exporting attestation manifest sha256:836ea6b531ce0a0efbf8ecbb3b34413176cd2151c7bbcb5f1111866a2f97a7b2 done
#11 exporting manifest list sha256:0ca9efa1a1f496f5a4f98578284bd82c56b889d31d7dd87a8bee7d59677f4ce1 done
#11 naming to docker.io/library/inventory:dev done
#11 unpacking to docker.io/library/inventory:dev
#11 unpacking to docker.io/library/inventory:dev 0.2s done
#11 DONE 0.9s
```

**Run the tests inside the image:**

```
docker run --rm inventory:dev pytest -q
```

The result was `153 passed`.

**Run the program.** A volume keeps the database between containers, so create the sample data once, then start the menu with `-it` (keyboard and terminal attached):

```
docker run --rm -v inventory_data:/data inventory:dev python seed_db.py
docker run -it --rm -v inventory_data:/data inventory:dev
```

### Persistence check

Data written in one container must still be there when a new container starts with the same volume. Real output (the menu was driven with `-i` and typed input instead of `-it`, so the commands could be scripted). Product 1 started with 40 in stock; the restock of 10 was made in one container and read back in a new one:

```
$ docker run --rm -v inventory_data:/data inventory:dev python seed_db.py
suppliers: 4
products: 12
sales: 5
sale_items: 12
stock_movements: 0

$ docker run -i --rm -v inventory_data:/data inventory:dev   (restock product 1 by 10, then quit)
Choose an option: Product id: Amount to add: Restocked. Claw Hammer now has 50 in stock.

$ docker run -i --rm -v inventory_data:/data inventory:dev   (a NEW container: look up product 1, then quit)
1 | HT-001 | Claw Hammer | Hand Tools | Acme Tools Co | 12.99 | 50 | 10
```

The stock of Claw Hammer is 50 in the new container, so the data survived. Without `-v inventory_data:/data` the data would be lost when the container is removed.
