import unittest
import warnings
from unittest.mock import patch
from py_appsheet.client import AppSheetClient


MOCK_ROWS = [
    {"name": "Alice", "email": "alice@example.com", "score": "42"},
    {"name": "Bob",   "email": "bob@example.com",   "score": "17"},
]

SCHEMA_WITH_PII = {
    "table_name": "TestTable",
    "source": "manual",
    "columns": [
        {"name": "name",  "contains_pii": True},
        {"name": "email", "contains_pii": True},
        {"name": "score", "contains_pii": False},
    ],
}

SCHEMA_NO_PII = {
    "table_name": "TestTable",
    "source": "manual",
    "columns": [
        {"name": "name",  "contains_pii": False},
        {"name": "email", "contains_pii": False},
        {"name": "score", "contains_pii": False},
    ],
}

SCHEMA_WITH_EXTRA_COLUMN = {
    "table_name": "TestTable",
    "source": "manual",
    "columns": [
        {"name": "name",   "contains_pii": False},
        {"name": "email",  "contains_pii": False},
        {"name": "score",  "contains_pii": False},
        {"name": "absent", "contains_pii": False},
    ],
}


class TestExportTable(unittest.TestCase):
    def setUp(self):
        self.client = AppSheetClient(app_id="test_app_id", api_key="test_api_key")

    def test_export_table_no_schema_returns_raw_rows(self):
        with patch.object(self.client, 'find_items', return_value=MOCK_ROWS):
            result = self.client.export_table("TestTable")
        self.assertEqual(result, MOCK_ROWS)

    def test_export_table_with_schema_normalizes_columns(self):
        with patch.object(self.client, 'find_items', return_value=MOCK_ROWS):
            result = self.client.export_table("TestTable", schema=SCHEMA_WITH_EXTRA_COLUMN)
        self.assertIn("absent", result[0])
        self.assertIsNone(result[0]["absent"])

    def test_export_table_column_order_matches_schema(self):
        with patch.object(self.client, 'find_items', return_value=MOCK_ROWS):
            result = self.client.export_table("TestTable", schema=SCHEMA_NO_PII)
        self.assertEqual(list(result[0].keys()), ["name", "email", "score"])

    def test_export_table_redact_pii_replaces_values(self):
        with patch.object(self.client, 'find_items', return_value=MOCK_ROWS):
            result = self.client.export_table("TestTable", schema=SCHEMA_WITH_PII, redact_pii=True)
        for row in result:
            self.assertEqual(row["name"], "[REDACTED]")
            self.assertEqual(row["email"], "[REDACTED]")
            self.assertNotEqual(row["score"], "[REDACTED]")

    def test_export_table_preserves_extra_columns_not_in_schema(self):
        rows_with_extra = [{"name": "Alice", "email": "a@example.com", "score": "42", "new_col": "surprise"}]
        with patch.object(self.client, 'find_items', return_value=rows_with_extra):
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always")
                result = self.client.export_table("TestTable", schema=SCHEMA_NO_PII)
        self.assertIn("new_col", result[0])
        self.assertEqual(result[0]["new_col"], "surprise")
        self.assertEqual(len(caught), 1)
        self.assertIn("not present in schema", str(caught[0].message))

    def test_export_table_redact_pii_without_schema_raises(self):
        with self.assertRaises(ValueError):
            self.client.export_table("TestTable", redact_pii=True)

    def test_export_table_warns_when_pii_not_redacted(self):
        with patch.object(self.client, 'find_items', return_value=MOCK_ROWS):
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always")
                self.client.export_table("TestTable", schema=SCHEMA_WITH_PII, redact_pii=False)
        self.assertEqual(len(caught), 1)
        self.assertIn("contains_pii=True", str(caught[0].message))

    def test_export_table_no_warning_when_no_pii_columns(self):
        with patch.object(self.client, 'find_items', return_value=MOCK_ROWS):
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always")
                self.client.export_table("TestTable", schema=SCHEMA_NO_PII, redact_pii=False)
        self.assertEqual(len(caught), 0)

    def test_export_table_no_warning_when_no_schema(self):
        with patch.object(self.client, 'find_items', return_value=MOCK_ROWS):
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always")
                self.client.export_table("TestTable")
        self.assertEqual(len(caught), 0)


class TestExportAllTables(unittest.TestCase):
    def setUp(self):
        self.client = AppSheetClient(app_id="test_app_id", api_key="test_api_key")

    def test_export_all_tables_returns_data_and_log(self):
        with patch.object(self.client, 'find_items', return_value=MOCK_ROWS):
            data, log = self.client.export_all_tables(["TestTable"])
        self.assertIn("TestTable", data)
        self.assertIn("status", log)

    def test_export_all_tables_complete_status(self):
        with patch.object(self.client, 'find_items', return_value=MOCK_ROWS):
            _, log = self.client.export_all_tables(["TestTable"])
        self.assertEqual(log["status"], "complete")
        self.assertEqual(len(log["exported"]), 1)
        self.assertEqual(len(log["failed"]), 0)

    def test_export_all_tables_partial_status_on_failure(self):
        def fail_one(table_name, **kwargs):
            if table_name == "BadTable":
                raise Exception("status 500")
            return MOCK_ROWS

        with patch.object(self.client, 'find_items', side_effect=fail_one):
            data, log = self.client.export_all_tables(["TestTable", "BadTable"])

        self.assertIn("TestTable", data)
        self.assertNotIn("BadTable", data)
        self.assertEqual(log["status"], "partial")
        self.assertEqual(len(log["failed"]), 1)
        self.assertEqual(log["failed"][0]["table"], "BadTable")

    def test_export_all_tables_log_row_counts(self):
        with patch.object(self.client, 'find_items', return_value=MOCK_ROWS):
            _, log = self.client.export_all_tables(["TestTable"])
        self.assertEqual(log["exported"][0]["row_count"], 2)

    def test_export_all_tables_uses_schema_per_table(self):
        schemas = {"TestTable": SCHEMA_WITH_PII}
        with patch.object(self.client, 'find_items', return_value=MOCK_ROWS):
            data, _ = self.client.export_all_tables(
                ["TestTable"], schemas=schemas, redact_pii=True
            )
        self.assertEqual(data["TestTable"][0]["name"], "[REDACTED]")

    def test_export_all_tables_redact_pii_skips_tables_without_schema(self):
        schemas = {"TableA": SCHEMA_WITH_PII}
        with patch.object(self.client, 'find_items', return_value=MOCK_ROWS):
            data, log = self.client.export_all_tables(
                ["TableA", "TableB"],
                schemas=schemas,
                redact_pii=True,
            )
        self.assertIn("TableA", data)
        self.assertIn("TableB", data)
        self.assertEqual(data["TableA"][0]["name"], "[REDACTED]")
        self.assertNotEqual(data["TableB"][0]["name"], "[REDACTED]")
        self.assertEqual(log["status"], "complete")

    def test_export_all_tables_redact_pii_in_log(self):
        with patch.object(self.client, 'find_items', return_value=MOCK_ROWS):
            _, log = self.client.export_all_tables(
                ["TestTable"], schemas={"TestTable": SCHEMA_WITH_PII}, redact_pii=True
            )
        self.assertTrue(log["redact_pii_requested"])
        self.assertIn("TestTable", log["redacted_tables"])
        self.assertEqual(log["unredacted_tables"], [])

    def test_export_all_tables_warns_and_logs_unredacted_tables(self):
        with patch.object(self.client, 'find_items', return_value=MOCK_ROWS):
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always")
                _, log = self.client.export_all_tables(["TestTable"], redact_pii=True)
        self.assertIn("TestTable", log["unredacted_tables"])
        self.assertEqual(log["redacted_tables"], [])
        self.assertTrue(any("without redaction" in str(w.message) for w in caught))

    def test_export_all_tables_log_has_timestamp(self):
        with patch.object(self.client, 'find_items', return_value=MOCK_ROWS):
            _, log = self.client.export_all_tables(["TestTable"])
        self.assertIn("timestamp", log)
        self.assertTrue(log["timestamp"].endswith("Z"))


if __name__ == '__main__':
    unittest.main()
