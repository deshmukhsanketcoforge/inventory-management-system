# Changelog

## 1.1.0 - 2026-11-03

### Added
- When the menu starts, a banner shows the number of low stock products.

## 1.0.0 - 2026-11-02

First release.

### Added
- SQLite database with five tables (suppliers, products, sales, sale items, stock movements), enforced by the database itself, and a seed script with sample data.
- Add, look up, change the price of, and delete products. A sold product cannot be deleted.
- Search by name, SKU or supplier, with category, maximum price, in stock and low stock filters.
- Four reports: stock value by supplier, low stock, sales by product, never sold.
- Restock, adjust stock, and record a sale. Each is one transaction, and every stock change is logged.
- Terminal menu with friendly messages for errors and bad input.
- Database backup with SQLite's backup function, and documented restore.
- Dockerfile with a pinned Python version, and a CI job that builds the image and runs the tests in it.
