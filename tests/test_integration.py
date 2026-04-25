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
from py_appsheet.schema import diff_schemas

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
# export tests
# ---------------------------------------------------------------------------

@pytest.mark.integration
class TestExport:

    def test_export_table_returns_list(self, client):
        """export_table returns a non-empty list of dicts."""
        rows = client.export_table(EXAMPLE_TABLE)
        assert isinstance(rows, list)
        assert len(rows) >= 1
        assert isinstance(rows[0], dict)

    def test_export_table_with_schema_normalizes_columns(self, client):
        """export_table with a schema ensures all schema columns are present in every row."""
        schema = {
            "table_name": EXAMPLE_TABLE,
            "source": "manual",
            "columns": [
                {"name": "Title Example", "contains_pii": False},
                {"name": "Assignee",      "contains_pii": False},
                {"name": "Status",        "contains_pii": False},
                {"name": "Another Column","contains_pii": False},
            ],
        }
        rows = client.export_table(EXAMPLE_TABLE, schema=schema)
        for row in rows:
            assert "Title Example" in row
            assert "Assignee" in row
            assert "Status" in row
            assert "Another Column" in row

    def test_export_table_redact_pii(self, client):
        """export_table with redact_pii=True replaces PII column values with [REDACTED]."""
        schema = {
            "table_name": EXAMPLE_TABLE,
            "source": "manual",
            "columns": [
                {"name": "Title Example", "contains_pii": True},
                {"name": "Assignee",      "contains_pii": False},
                {"name": "Status",        "contains_pii": False},
                {"name": "Another Column","contains_pii": False},
            ],
        }
        rows = client.export_table(EXAMPLE_TABLE, schema=schema, redact_pii=True)
        for row in rows:
            assert row["Title Example"] == "[REDACTED]"
            assert row["Assignee"] != "[REDACTED]"

    def test_export_all_tables_returns_data_and_log(self, client):
        """export_all_tables returns data dict and a complete log."""
        data, log = client.export_all_tables([EXAMPLE_TABLE])
        assert EXAMPLE_TABLE in data
        assert isinstance(data[EXAMPLE_TABLE], list)
        assert log["status"] == "complete"
        assert len(log["exported"]) == 1
        assert len(log["failed"]) == 0

    def test_export_all_tables_partial_on_bad_table(self, client):
        """export_all_tables logs failures for non-existent tables and continues."""
        data, log = client.export_all_tables([EXAMPLE_TABLE, "nonexistent_table_xyz"])
        assert EXAMPLE_TABLE in data
        assert log["status"] == "partial"
        assert any(f["table"] == "nonexistent_table_xyz" for f in log["failed"])


# ---------------------------------------------------------------------------
# schema tests
# ---------------------------------------------------------------------------

@pytest.mark.integration
class TestSchema:

    def test_infer_schema_returns_expected_structure(self, client):
        """infer_schema returns a valid schema dict with required top-level keys."""
        schema = client.infer_schema(EXAMPLE_TABLE)
        assert schema["table_name"] == EXAMPLE_TABLE
        assert schema["source"] == "data_inference"
        assert schema["appsheet_app_id"] is not None
        assert isinstance(schema["row_count"], int)
        assert isinstance(schema["columns"], list)
        assert len(schema["columns"]) >= 1

    def test_infer_schema_column_structure(self, client):
        """Each column in the inferred schema has required fields."""
        schema = client.infer_schema(EXAMPLE_TABLE)
        for col in schema["columns"]:
            assert "name" in col
            assert "inferred_type" in col
            assert "nullable" in col
            assert "contains_pii" in col
            assert col["contains_pii"] is False

    def test_infer_schema_known_columns_present(self, client):
        """infer_schema captures the known columns of example_table."""
        schema = client.infer_schema(EXAMPLE_TABLE)
        names = [col["name"] for col in schema["columns"]]
        assert "Title Example" in names

    def test_infer_schema_uses_pre_fetched_rows(self, client):
        """infer_schema accepts pre-fetched rows and does not make an extra API call."""
        rows = client.export_table(EXAMPLE_TABLE)
        schema = client.infer_schema(EXAMPLE_TABLE, rows=rows)
        assert schema["row_count"] == len(rows)

    def test_diff_schemas_no_change(self, client):
        """diff_schemas reports no changes when the same schema is compared to itself."""
        schema = client.infer_schema(EXAMPLE_TABLE)
        diff = diff_schemas(schema, schema)
        assert diff["added"] == []
        assert diff["removed"] == []
        assert diff["type_changed"] == []
        assert len(diff["unchanged"]) == len(schema["columns"])

    def test_diff_schemas_detects_added_column(self, client):
        """diff_schemas correctly identifies a newly added column."""
        schema = client.infer_schema(EXAMPLE_TABLE)
        new_schema = {**schema, "columns": schema["columns"] + [
            {"name": "new_col", "inferred_type": "string", "contains_pii": False, "nullable": True}
        ]}
        diff = diff_schemas(schema, new_schema)
        assert "new_col" in diff["added"]


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
