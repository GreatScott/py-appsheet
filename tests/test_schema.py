import unittest
from unittest.mock import patch
from py_appsheet.client import AppSheetClient
from py_appsheet.schema import diff_schemas


MOCK_ROWS = [
    {"id": "1", "name": "Alice", "score": "42",   "active": "true",  "created": "2024-01-15"},
    {"id": "2", "name": "Bob",   "score": "17",   "active": "false", "created": "2024-03-22"},
    {"id": "3", "name": "Carol", "score": "3.14", "active": "true",  "created": "2024-06-01"},
]

MOCK_ROWS_WITH_BLANKS = [
    {"id": "1", "name": "Alice", "notes": ""},
    {"id": "2", "name": "Bob",   "notes": None},
]


class TestInferSchema(unittest.TestCase):
    def setUp(self):
        self.client = AppSheetClient(app_id="test_app_id", api_key="test_api_key")

    def _infer(self, rows=None):
        with patch.object(self.client, 'find_items', return_value=rows or MOCK_ROWS):
            return self.client.infer_schema("TestTable")

    def test_returns_correct_table_name(self):
        schema = self._infer()
        self.assertEqual(schema["table_name"], "TestTable")

    def test_returns_correct_app_id(self):
        schema = self._infer()
        self.assertEqual(schema["appsheet_app_id"], "test_app_id")

    def test_source_is_data_inference(self):
        schema = self._infer()
        self.assertEqual(schema["source"], "data_inference")

    def test_row_count(self):
        schema = self._infer()
        self.assertEqual(schema["row_count"], 3)

    def test_captured_at_present(self):
        schema = self._infer()
        self.assertIn("captured_at", schema)
        self.assertTrue(schema["captured_at"].endswith("Z"))

    def test_column_names(self):
        schema = self._infer()
        names = [col["name"] for col in schema["columns"]]
        self.assertIn("id", names)
        self.assertIn("name", names)
        self.assertIn("score", names)
        self.assertIn("active", names)
        self.assertIn("created", names)

    def test_contains_pii_defaults_false(self):
        schema = self._infer()
        for col in schema["columns"]:
            self.assertFalse(col["contains_pii"])

    def test_infers_integer_type(self):
        rows = [{"val": "1"}, {"val": "2"}, {"val": "42"}]
        schema = self._infer(rows)
        col = next(c for c in schema["columns"] if c["name"] == "val")
        self.assertEqual(col["inferred_type"], "integer")

    def test_infers_number_type(self):
        rows = [{"val": "3.14"}, {"val": "2.71"}, {"val": "1.0"}]
        schema = self._infer(rows)
        col = next(c for c in schema["columns"] if c["name"] == "val")
        self.assertEqual(col["inferred_type"], "number")

    def test_infers_boolean_type(self):
        rows = [{"val": "true"}, {"val": "false"}, {"val": "True"}]
        schema = self._infer(rows)
        col = next(c for c in schema["columns"] if c["name"] == "val")
        self.assertEqual(col["inferred_type"], "boolean")

    def test_infers_datetime_type(self):
        rows = [{"val": "2024-01-15"}, {"val": "2024-03-22"}]
        schema = self._infer(rows)
        col = next(c for c in schema["columns"] if c["name"] == "val")
        self.assertEqual(col["inferred_type"], "datetime")

    def test_infers_string_type(self):
        rows = [{"val": "hello"}, {"val": "world"}]
        schema = self._infer(rows)
        col = next(c for c in schema["columns"] if c["name"] == "val")
        self.assertEqual(col["inferred_type"], "string")

    def test_infers_unknown_for_all_blank(self):
        rows = [{"val": ""}, {"val": None}]
        schema = self._infer(rows)
        col = next(c for c in schema["columns"] if c["name"] == "val")
        self.assertEqual(col["inferred_type"], "unknown")

    def test_nullable_true_when_blank_present(self):
        schema = self._infer(MOCK_ROWS_WITH_BLANKS)
        col = next(c for c in schema["columns"] if c["name"] == "notes")
        self.assertTrue(col["nullable"])

    def test_nullable_false_when_no_blanks(self):
        schema = self._infer(MOCK_ROWS)
        col = next(c for c in schema["columns"] if c["name"] == "id")
        self.assertFalse(col["nullable"])

    def test_uses_pre_fetched_rows(self):
        with patch.object(self.client, 'find_items') as mock_find:
            self.client.infer_schema("TestTable", rows=MOCK_ROWS)
        mock_find.assert_not_called()

    def test_fetches_internally_when_no_rows(self):
        with patch.object(self.client, 'find_items', return_value=MOCK_ROWS) as mock_find:
            self.client.infer_schema("TestTable")
        mock_find.assert_called_once()


class TestInferAllSchemas(unittest.TestCase):
    def setUp(self):
        self.client = AppSheetClient(app_id="test_app_id", api_key="test_api_key")

    def test_infer_all_schemas_returns_dict_keyed_by_table(self):
        with patch.object(self.client, 'find_items', return_value=MOCK_ROWS):
            schemas = self.client.infer_all_schemas(["TableA", "TableB"])
        self.assertIn("TableA", schemas)
        self.assertIn("TableB", schemas)
        self.assertEqual(schemas["TableA"]["table_name"], "TableA")
        self.assertEqual(schemas["TableB"]["table_name"], "TableB")

    def test_infer_all_schemas_empty_list(self):
        schemas = self.client.infer_all_schemas([])
        self.assertEqual(schemas, {})


class TestDiffSchemas(unittest.TestCase):
    def _schema(self, columns):
        return {
            "table_name": "T",
            "source": "manual",
            "columns": columns,
        }

    def test_no_changes(self):
        schema = self._schema([
            {"name": "id", "inferred_type": "integer"},
            {"name": "name", "inferred_type": "string"},
        ])
        diff = diff_schemas(schema, schema)
        self.assertEqual(diff["added"], [])
        self.assertEqual(diff["removed"], [])
        self.assertEqual(diff["type_changed"], [])
        self.assertEqual(sorted(diff["unchanged"]), ["id", "name"])

    def test_detects_added_column(self):
        old = self._schema([{"name": "id", "inferred_type": "integer"}])
        new = self._schema([
            {"name": "id", "inferred_type": "integer"},
            {"name": "email", "inferred_type": "string"},
        ])
        diff = diff_schemas(old, new)
        self.assertIn("email", diff["added"])

    def test_detects_removed_column(self):
        old = self._schema([
            {"name": "id", "inferred_type": "integer"},
            {"name": "email", "inferred_type": "string"},
        ])
        new = self._schema([{"name": "id", "inferred_type": "integer"}])
        diff = diff_schemas(old, new)
        self.assertIn("email", diff["removed"])

    def test_detects_type_change(self):
        old = self._schema([{"name": "score", "inferred_type": "string"}])
        new = self._schema([{"name": "score", "inferred_type": "integer"}])
        diff = diff_schemas(old, new)
        self.assertEqual(len(diff["type_changed"]), 1)
        self.assertEqual(diff["type_changed"][0]["column"], "score")
        self.assertEqual(diff["type_changed"][0]["old_type"], "string")
        self.assertEqual(diff["type_changed"][0]["new_type"], "integer")

    def test_works_with_appsheet_type(self):
        old = self._schema([{"name": "col", "appsheet_type": "Text"}])
        new = self._schema([{"name": "col", "appsheet_type": "DateTime"}])
        diff = diff_schemas(old, new)
        self.assertEqual(len(diff["type_changed"]), 1)


if __name__ == '__main__':
    unittest.main()
