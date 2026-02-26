"""
Integration tests against a real AppSheet database.

Requires APP_ID and ACCESS_KEY in a .env file at the project root.
Run with: pytest -m integration

Tables expected:
  - example_table: columns "Title Example" (key), "Assignee", "Status", "Date", "Another Column"
  - dual_key_table: columns "keycol1" (key), "keycol2" (key), "val" (NOT a key)
      AppSheet composite key column: "_ComputedKey" = "keycol1: keycol2"

NOTE on dual_key_table setup: In AppSheet's column editor, ensure that ONLY
"keycol1" and "keycol2" have the "Key" checkbox checked. "val" must NOT be a key.
If all three are marked as keys, _ComputedKey will be a 3-part value and the
composite key tests will fail.
"""
import pytest
from py_appsheet.utils import build_composite_key, build_selector

EXAMPLE_TABLE = "example_table"
DUAL_KEY_TABLE = "dual_key_table"

# Sentinel values that identify rows created by these tests
TEST_TITLE = "pytest_integration_test_row"
TEST_KEY1 = "pytest_key1"
TEST_KEY2 = "pytest_key2"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def example_row(client):
    """Add a test row to example_table and clean up after the test."""
    row = {
        "Title Example": TEST_TITLE,
        "Assignee": "pytest",
        "Status": "Not Started",
        "Another Column": "initial value",
    }
    client.add_items(EXAMPLE_TABLE, [row])
    yield row
    try:
        client.delete_item(EXAMPLE_TABLE, "Title Example", TEST_TITLE)
    except Exception:
        pass  # Already deleted by the test itself


@pytest.fixture
def dual_key_row(client):
    """Add a test row to dual_key_table and clean up after the test.

    Requires dual_key_table to have keycol1 and keycol2 as keys, val as non-key.
    """
    row = {
        "keycol1": TEST_KEY1,
        "keycol2": TEST_KEY2,
        "val": "initial value",
    }
    client.add_items(DUAL_KEY_TABLE, [row])
    yield row
    try:
        client.delete_item(DUAL_KEY_TABLE, {"keycol1": TEST_KEY1, "keycol2": TEST_KEY2})
    except Exception:
        pass  # Already deleted by the test itself


# ---------------------------------------------------------------------------
# example_table tests
# ---------------------------------------------------------------------------

@pytest.mark.integration
class TestExampleTable:

    def test_add_and_find_local_filter(self, client, example_row):
        """add_items creates a row that find_items can locate via local filtering."""
        results = client.find_items(EXAMPLE_TABLE, TEST_TITLE, target_column="Title Example")
        assert len(results) == 1
        assert results[0]["Title Example"] == TEST_TITLE

    def test_find_with_selector(self, client, example_row):
        """find_items with a selector expression returns only matching rows."""
        selector = build_selector(EXAMPLE_TABLE, "Title Example", TEST_TITLE)
        results = client.find_items(EXAMPLE_TABLE, selector=selector)
        assert any(r["Title Example"] == TEST_TITLE for r in results)

    def test_find_no_filter_returns_rows(self, client, example_row):
        """find_items with no filter returns all rows (at least our test row)."""
        results = client.find_items(EXAMPLE_TABLE)
        assert isinstance(results, list)
        assert len(results) >= 1

    def test_edit_item(self, client, example_row):
        """edit_item updates a column value on an existing row."""
        client.edit_item(
            EXAMPLE_TABLE,
            "Title Example",
            {"Title Example": TEST_TITLE, "Another Column": "edited value"},
        )
        results = client.find_items(EXAMPLE_TABLE, TEST_TITLE, target_column="Title Example")
        assert results[0]["Another Column"] == "edited value"

    def test_edit_item_status(self, client, example_row):
        """edit_item can update an enum column."""
        client.edit_item(
            EXAMPLE_TABLE,
            "Title Example",
            {"Title Example": TEST_TITLE, "Status": "In Progress"},
        )
        results = client.find_items(EXAMPLE_TABLE, TEST_TITLE, target_column="Title Example")
        assert results[0]["Status"] == "In Progress"

    def test_delete_item(self, client, example_row):
        """delete_item removes the row; subsequent find returns empty."""
        client.delete_item(EXAMPLE_TABLE, "Title Example", TEST_TITLE)
        results = client.find_items(EXAMPLE_TABLE, TEST_TITLE, target_column="Title Example")
        assert len(results) == 0

    def test_delete_row_alias(self, client, example_row):
        """delete_row (backwards-compat alias) behaves identically to delete_item."""
        client.delete_row(EXAMPLE_TABLE, "Title Example", TEST_TITLE)
        results = client.find_items(EXAMPLE_TABLE, TEST_TITLE, target_column="Title Example")
        assert len(results) == 0


# ---------------------------------------------------------------------------
# dual_key_table tests
# ---------------------------------------------------------------------------

@pytest.mark.integration
class TestDualKeyTable:

    def test_build_composite_key_format(self):
        """build_composite_key produces the expected AppSheet _ComputedKey format."""
        key = build_composite_key(TEST_KEY1, TEST_KEY2)
        assert key == f"{TEST_KEY1}: {TEST_KEY2}"

    def test_add_and_find_by_composite_key(self, client, dual_key_row):
        """Rows with composite keys can be found by matching the _ComputedKey column."""
        expected_key = build_composite_key(TEST_KEY1, TEST_KEY2)
        results = client.find_items(DUAL_KEY_TABLE, expected_key, target_column="_ComputedKey")
        assert len(results) == 1
        assert results[0]["keycol1"] == TEST_KEY1
        assert results[0]["keycol2"] == TEST_KEY2

    def test_edit_via_composite_key_columns(self, client, dual_key_row):
        """edit_item works for composite-key tables: include all key columns + updated fields.

        For composite-key tables, pass any one key column as key_column and include
        ALL key columns plus the fields to update in row_data. AppSheet identifies the
        row from all key columns present in the row.
        """
        client.edit_item(
            DUAL_KEY_TABLE,
            "keycol1",
            {"keycol1": TEST_KEY1, "keycol2": TEST_KEY2, "val": "edited value"},
        )
        expected_key = build_composite_key(TEST_KEY1, TEST_KEY2)
        results = client.find_items(DUAL_KEY_TABLE, expected_key, target_column="_ComputedKey")
        assert results[0]["val"] == "edited value"

    def test_delete_via_composite_key_dict(self, client, dual_key_row):
        """delete_item accepts a dict of key column values for composite-key tables."""
        client.delete_item(DUAL_KEY_TABLE, {"keycol1": TEST_KEY1, "keycol2": TEST_KEY2})
        expected_key = build_composite_key(TEST_KEY1, TEST_KEY2)
        results = client.find_items(DUAL_KEY_TABLE, expected_key, target_column="_ComputedKey")
        assert len(results) == 0
