from contextlib import closing

import pytest

import main
from inventory_db import connect

HAMMER = 1
CONCRETE_MIX = 5


def run_menu_with(db, monkeypatch, capsys, answers):
    """Run the menu with these typed answers (end with '0' to quit) and return its output."""
    answers = iter(answers)
    monkeypatch.setattr("builtins.input", lambda prompt="": next(answers))
    main.run_menu(db)
    return capsys.readouterr().out


def stock_of(db, product_id):
    return db.execute(
        "SELECT quantity_in_stock FROM products WHERE product_id = ?", (product_id,)
    ).fetchone()[0]


@pytest.mark.parametrize(
    "cents, text", [(1299, "12.99"), (5, "0.05"), (0, "0.00"), (100000, "1000.00")]
)
def test_money_is_shown_with_two_decimals(cents, text):
    assert main.format_money(cents) == text


@pytest.mark.parametrize(
    "text, cents", [("12.99", 1299), ("5", 500), ("0.5", 50), (" 7.10 ", 710), ("0", 0)]
)
def test_prices_are_turned_into_whole_cents(text, cents):
    assert main.parse_money(text) == cents


@pytest.mark.parametrize("text", ["abc", "", "nan", "inf"])
def test_unusable_prices_are_refused(text):
    with pytest.raises(main.InputError):
        main.parse_money(text)


@pytest.mark.parametrize("text", ["five", "", "2.5"])
def test_unusable_whole_numbers_are_refused(text):
    with pytest.raises(main.InputError):
        main.parse_whole_number(text)


def test_a_bad_menu_choice_and_text_instead_of_a_number_do_not_crash(db, monkeypatch, capsys):
    # "x" is not an option; option 4 (restock) is given "abc" as the product id.
    output = run_menu_with(db, monkeypatch, capsys, ["x", "4", "abc", "0"])
    assert "Please type a number from the menu." in output
    assert "'abc' is not a whole number." in output


def test_search_shows_matching_products_with_prices(db, monkeypatch, capsys):
    output = run_menu_with(db, monkeypatch, capsys, ["1", "hammer", "", "", "n", "n", "0"])
    assert "Claw Hammer" in output
    assert "12.99" in output
    assert "Garden Hose" not in output


def test_search_with_a_bad_price_filter_shows_an_error(db, monkeypatch, capsys):
    output = run_menu_with(db, monkeypatch, capsys, ["1", "", "", "cheap", "0"])
    assert "'cheap' is not a price like 12.99." in output


def test_looking_up_a_missing_product_says_so(db, monkeypatch, capsys):
    output = run_menu_with(db, monkeypatch, capsys, ["2", "999", "0"])
    assert "No product with id 999." in output


def test_adding_a_product_through_the_menu(db, monkeypatch, capsys):
    answers = ["3", "HT-099", "Tape Measure", "Hand Tools", "1", "7.99", "15", "5", "0"]
    output = run_menu_with(db, monkeypatch, capsys, answers)
    assert "Added product 13." in output
    price = db.execute("SELECT unit_price FROM products WHERE sku = 'HT-099'").fetchone()[0]
    assert price == 799


def test_adding_a_duplicate_sku_shows_a_friendly_message(db, monkeypatch, capsys):
    answers = ["3", "HT-001", "Another Hammer", "Hand Tools", "1", "7.99", "15", "5", "0"]
    output = run_menu_with(db, monkeypatch, capsys, answers)
    assert "Error: A product with this SKU already exists." in output


def test_restocking_through_the_menu(db, monkeypatch, capsys):
    output = run_menu_with(db, monkeypatch, capsys, ["4", str(HAMMER), "10", "0"])
    assert "Claw Hammer now has 50 in stock." in output
    assert stock_of(db, HAMMER) == 50


def test_restocking_zero_shows_a_friendly_message(db, monkeypatch, capsys):
    output = run_menu_with(db, monkeypatch, capsys, ["4", str(HAMMER), "0", "0"])
    assert "Error: A restock amount must be more than zero." in output
    assert stock_of(db, HAMMER) == 40


def test_recording_a_sale_through_the_menu(db, monkeypatch, capsys):
    answers = ["5", str(HAMMER), "2", str(CONCRETE_MIX), "1", "", "0"]
    output = run_menu_with(db, monkeypatch, capsys, answers)
    assert "Sale 6 recorded." in output
    assert stock_of(db, HAMMER) == 38
    assert stock_of(db, CONCRETE_MIX) == 4


def test_a_failing_sale_shows_an_error_and_changes_nothing(db, monkeypatch, capsys):
    answers = ["5", str(HAMMER), "2", str(CONCRETE_MIX), "6", "", "0"]
    output = run_menu_with(db, monkeypatch, capsys, answers)
    assert "Error: Not enough stock of product 5" in output
    assert stock_of(db, HAMMER) == 40
    assert db.execute("SELECT COUNT(*) FROM sales").fetchone()[0] == 5


@pytest.mark.parametrize(
    "option, expected",
    [
        ("6", "BuildRight Supply | 1453.57"),
        ("7", "Concrete Mix 20kg"),
        ("8", "Wood Screws Box"),
        ("9", "Garden Gloves"),
    ],
)
def test_each_report_can_be_run_from_the_menu(db, monkeypatch, capsys, option, expected):
    output = run_menu_with(db, monkeypatch, capsys, [option, "0"])
    assert expected in output


def test_backing_up_through_the_menu_writes_a_copy(db, monkeypatch, capsys, tmp_path):
    backup_path = tmp_path / "backup.db"
    output = run_menu_with(db, monkeypatch, capsys, ["10", str(backup_path), "0"])
    assert f"Backup saved to {backup_path}." in output
    with closing(connect(backup_path)) as backup:
        assert backup.execute("SELECT COUNT(*) FROM products").fetchone()[0] == 12


def test_a_backup_to_a_missing_folder_creates_the_folder(db, monkeypatch, capsys, tmp_path):
    backup_path = tmp_path / "new_folder" / "backup.db"
    output = run_menu_with(db, monkeypatch, capsys, ["10", str(backup_path), "0"])
    assert f"Backup saved to {backup_path}." in output
    assert backup_path.exists()


def test_a_backup_that_cannot_be_written_shows_a_database_error(db, monkeypatch, capsys, tmp_path):
    # tmp_path is a folder, so it cannot be used as the backup file
    output = run_menu_with(db, monkeypatch, capsys, ["10", str(tmp_path), "0"])
    assert "Database error:" in output


def test_the_menu_starts_with_the_number_of_low_stock_products(db, monkeypatch, capsys):
    output = run_menu_with(db, monkeypatch, capsys, ["0"])
    assert output.startswith("*** Low stock products: 4 ***")


def test_the_banner_shows_zero_when_nothing_is_low(empty_db, monkeypatch, capsys):
    output = run_menu_with(empty_db, monkeypatch, capsys, ["0"])
    assert "*** Low stock products: 0 ***" in output


def test_the_banner_is_shown_only_once(db, monkeypatch, capsys):
    output = run_menu_with(db, monkeypatch, capsys, ["x", "x", "0"])
    assert output.count("Low stock products:") == 1