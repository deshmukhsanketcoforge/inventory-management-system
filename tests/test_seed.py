import pytest

from seed_db import main, print_row_counts


@pytest.mark.parametrize(
    "table, expected",
    [
        ("suppliers", 4),
        ("products", 12),
        ("sales", 5),
        ("sale_items", 12),
        ("stock_movements", 0),
    ],
)
def test_seed_row_counts(db, table, expected):
    count = db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    assert count == expected


def test_seed_has_at_least_three_categories(db):
    categories = db.execute("SELECT DISTINCT category FROM products").fetchall()
    assert len(categories) >= 3


def test_seed_has_at_least_two_products_never_sold(db):
    never_sold = db.execute(
        "SELECT COUNT(*) FROM products WHERE product_id NOT IN"
        " (SELECT product_id FROM sale_items)"
    ).fetchone()[0]
    assert never_sold >= 2


def test_seed_has_at_least_two_products_at_or_below_reorder_level(db):
    low = db.execute(
        "SELECT COUNT(*) FROM products WHERE quantity_in_stock <= reorder_level"
    ).fetchone()[0]
    assert low >= 2


def test_sale_items_use_the_products_current_price(db):
    mismatches = db.execute(
        "SELECT COUNT(*) FROM sale_items JOIN products USING (product_id)"
        " WHERE price_charged_per_unit != unit_price"
    ).fetchone()[0]
    assert mismatches == 0


def test_print_row_counts_shows_every_table(db, capsys):
    print_row_counts(db)
    output = capsys.readouterr().out
    assert "suppliers: 4" in output
    assert "stock_movements: 0" in output


def test_running_the_seed_twice_keeps_one_copy_of_the_data(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("INVENTORY_DB", str(tmp_path / "seed.db"))
    main()
    main()
    output = capsys.readouterr().out
    assert "skipping sample data" in output
    assert output.count("products: 12") == 2
