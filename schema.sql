CREATE TABLE IF NOT EXISTS suppliers (
    supplier_id INTEGER PRIMARY KEY,
    name        TEXT NOT NULL UNIQUE CHECK (trim(name) != '')
) STRICT;

CREATE TABLE IF NOT EXISTS products (
    product_id        INTEGER PRIMARY KEY,
    sku               TEXT NOT NULL UNIQUE CHECK (trim(sku) != ''),
    name              TEXT NOT NULL CHECK (trim(name) != ''),
    category          TEXT NOT NULL CHECK (trim(category) != ''),
    supplier_id       INTEGER NOT NULL REFERENCES suppliers (supplier_id),
    unit_price        INTEGER NOT NULL CHECK (unit_price >= 0),
    quantity_in_stock INTEGER NOT NULL DEFAULT 0 CHECK (quantity_in_stock >= 0),
    reorder_level     INTEGER NOT NULL CHECK (reorder_level >= 0)
) STRICT;

CREATE INDEX IF NOT EXISTS idx_products_supplier ON products (supplier_id);

CREATE TABLE IF NOT EXISTS sales (
    sale_id INTEGER PRIMARY KEY,
    sold_at TEXT NOT NULL
) STRICT;

CREATE TABLE IF NOT EXISTS sale_items (
    sale_id                INTEGER NOT NULL REFERENCES sales (sale_id),
    product_id             INTEGER NOT NULL REFERENCES products (product_id),
    quantity               INTEGER NOT NULL CHECK (quantity > 0),
    price_charged_per_unit INTEGER NOT NULL CHECK (price_charged_per_unit >= 0),
    PRIMARY KEY (sale_id, product_id)
) STRICT;

CREATE INDEX IF NOT EXISTS idx_sale_items_product ON sale_items (product_id);

CREATE TABLE IF NOT EXISTS stock_movements (
    movement_id INTEGER PRIMARY KEY,
    product_id  INTEGER NOT NULL REFERENCES products (product_id),
    change      INTEGER NOT NULL CHECK (change != 0),
    reason      TEXT NOT NULL CHECK (reason IN ('restock', 'adjustment', 'sale')),
    occurred_at TEXT NOT NULL
) STRICT;
