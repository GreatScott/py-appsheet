import unittest
from unittest.mock import patch
from py_appsheet.client import AppSheetClient
from py_appsheet.utils import build_composite_key, build_selector


class TestAppSheetClient(unittest.TestCase):
    def setUp(self):
        self.client = AppSheetClient(app_id="test_app_id", api_key="test_api_key")

    # --- find_items ---

    def test_find_items_found(self):
        mock_response = [
            {"Email": "test@example.com", "Name": "John Doe", "ID": "123"}
        ]
        with patch.object(self.client, '_make_request', return_value=mock_response):
            result = self.client.find_items("Patients", "test@example.com", target_column="Email")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["Email"], "test@example.com")

    def test_find_items_not_found(self):
        mock_response = [
            {"Email": "test@example.com", "Name": "John Doe", "ID": "123"}
        ]
        with patch.object(self.client, '_make_request', return_value=mock_response):
            result = self.client.find_items("Patients", "nonexistent@example.com", target_column="Email")
        self.assertEqual(len(result), 0)

    def test_find_items_malformed_response(self):
        with patch.object(self.client, '_make_request', return_value={}):
            with self.assertRaises(ValueError) as ctx:
                self.client.find_items("Patients", "test@example.com", target_column="Email")
        self.assertIn("Expected a list of rows", str(ctx.exception))

    def test_find_items_api_error(self):
        with patch.object(self.client, '_make_request', side_effect=Exception("API Error")):
            with self.assertRaises(Exception) as ctx:
                self.client.find_items("Patients", "test@example.com", target_column="Email")
        self.assertIn("API Error", str(ctx.exception))

    def test_find_items_in_any_column(self):
        mock_response = [
            {"Email": "test@example.com", "Name": "John Doe", "ID": "123"},
            {"Email": "another@example.com", "Name": "Jane Smith", "ID": "456"},
        ]
        with patch.object(self.client, '_make_request', return_value=mock_response):
            result = self.client.find_items("Patients", "John Doe")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["Name"], "John Doe")

    def test_find_items_no_filter_returns_all(self):
        mock_response = [
            {"Email": "a@example.com", "Name": "Alice"},
            {"Email": "b@example.com", "Name": "Bob"},
        ]
        with patch.object(self.client, '_make_request', return_value=mock_response):
            result = self.client.find_items("Patients")
        self.assertEqual(len(result), 2)

    def test_find_items_with_selector_passes_to_payload(self):
        mock_response = [{"Status": "In Progress", "ID": "1"}]
        with patch.object(self.client, '_make_request', return_value=mock_response) as mock_req:
            result = self.client.find_items("Tasks", selector="Filter(Tasks, [Status] = 'In Progress')")
        payload = mock_req.call_args[0][2]
        self.assertEqual(payload["Properties"]["Selector"], "Filter(Tasks, [Status] = 'In Progress')")
        self.assertEqual(len(result), 1)

    def test_find_items_selector_with_local_filter(self):
        # Selector narrows server-side; item/target_column refines locally
        mock_response = [
            {"Status": "In Progress", "Assignee": "Alice"},
            {"Status": "In Progress", "Assignee": "Bob"},
        ]
        with patch.object(self.client, '_make_request', return_value=mock_response):
            result = self.client.find_items(
                "Tasks",
                item="Alice",
                target_column="Assignee",
                selector="Filter(Tasks, [Status] = 'In Progress')",
            )
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["Assignee"], "Alice")

    # --- add_items ---

    def test_add_items(self):
        rows = [{"Serial Number Hex": "ABC123", "SKU": "SKU123"}]
        mock_response = {"status": "OK"}
        with patch.object(self.client, '_make_request', return_value=mock_response):
            response = self.client.add_items("Inventory Table", rows)
        self.assertEqual(response["status"], "OK")

    # --- edit_item ---

    def test_edit_item(self):
        row_data = {
            "Serial Number Hex": "ABC123",
            "Bar Code": "some_barcode.svg",
        }
        mock_response = {"status": "OK"}
        with patch.object(self.client, '_make_request', return_value=mock_response):
            response = self.client.edit_item("Inventory Table", "Serial Number Hex", row_data)
        self.assertEqual(response["status"], "OK")

    def test_edit_item_missing_key_column_raises(self):
        row_data = {"Bar Code": "some_barcode.svg"}
        with self.assertRaises(ValueError) as ctx:
            self.client.edit_item("Inventory Table", "Serial Number Hex", row_data)
        self.assertIn("Serial Number Hex", str(ctx.exception))

    # --- delete_item / delete_row ---

    def test_delete_item(self):
        mock_response = {"status": "OK"}
        with patch.object(self.client, '_make_request', return_value=mock_response):
            response = self.client.delete_item("Inventory Table", "Serial Number Hex", "ABC123")
        self.assertEqual(response["status"], "OK")

    def test_delete_item_composite_key(self):
        mock_response = {"status": "OK"}
        with patch.object(self.client, '_make_request', return_value=mock_response) as mock_req:
            response = self.client.delete_item("My Table", {"keycol1": "v1", "keycol2": "v2"})
        payload = mock_req.call_args[0][2]
        self.assertEqual(payload["Rows"], [{"keycol1": "v1", "keycol2": "v2"}])
        self.assertEqual(response["status"], "OK")

    def test_delete_row_is_alias_for_delete_item(self):
        mock_response = {"status": "OK"}
        with patch.object(self.client, '_make_request', return_value=mock_response):
            response = self.client.delete_row("Inventory Table", "Serial Number Hex", "ABC123")
        self.assertEqual(response["status"], "OK")


class TestUtils(unittest.TestCase):

    def test_build_composite_key_two_values(self):
        self.assertEqual(build_composite_key("foo", "bar"), "foo: bar")

    def test_build_composite_key_three_values(self):
        self.assertEqual(build_composite_key("a", "b", "c"), "a: b: c")

    def test_build_composite_key_custom_separator(self):
        self.assertEqual(build_composite_key("x", "y", separator="|"), "x|y")

    def test_build_composite_key_non_string_values(self):
        self.assertEqual(build_composite_key(1, 2), "1: 2")

    def test_build_selector_default_operator(self):
        result = build_selector("Tasks", "Status", "In Progress")
        self.assertEqual(result, "Filter(Tasks, [Status] = 'In Progress')")

    def test_build_selector_custom_operator(self):
        result = build_selector("Tasks", "Priority", "3", operator=">=")
        self.assertEqual(result, "Filter(Tasks, [Priority] >= '3')")


if __name__ == '__main__':
    unittest.main()
