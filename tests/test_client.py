import unittest
from unittest.mock import patch, MagicMock
from py_appsheet.client import AppSheetClient

class TestAppSheetClient(unittest.TestCase):
    def setUp(self):
        self.app_id = "test_app_id"
        self.api_key = "test_api_key"
        self.client = AppSheetClient(app_id=self.app_id, api_key=self.api_key)

    def test_find_items_found(self):
        table_name = "Patients"
        item = "test@example.com"
        key_column = "Email"

        mock_response = {
            "Rows": [
                {"Email": "test@example.com", "Name": "John Doe", "ID": "123"}
            ]
        }

        with patch.object(self.client, '_make_request', return_value=mock_response):
            result = self.client.find_items(table_name, item, key_column)
            self.assertEqual(len(result), 1)
            self.assertEqual(result[0]["Email"], item)

    def test_find_items_not_found(self):
        table_name = "Patients"
        item = "nonexistent@example.com"
        key_column = "Email"

        mock_response = {
            "Rows": [
                {"Email": "test@example.com", "Name": "John Doe", "ID": "123"}
            ]
        }

        with patch.object(self.client, '_make_request', return_value=mock_response):
            result = self.client.find_items(table_name, item, key_column)
            self.assertEqual(len(result), 0)

    def test_find_items_malformed_response(self):
        table_name = "Patients"
        item = "test@example.com"
        key_column = "Email"

        mock_response = {}

        with patch.object(self.client, '_make_request', return_value=mock_response):
            with self.assertRaises(ValueError) as context:
                self.client.find_items(table_name, item, key_column)
            self.assertIn("Unexpected response format or missing 'Rows' key", str(context.exception))

    def test_find_items_api_error(self):
        table_name = "Patients"
        item = "test@example.com"
        key_column = "Email"

        with patch.object(self.client, '_make_request', side_effect=Exception("API Error")):
            with self.assertRaises(Exception) as context:
                self.client.find_items(table_name, item, key_column)
            self.assertIn("API Error", str(context.exception))

    def test_find_items_in_any_column(self):
        table_name = "Patients"
        item = "John Doe"

        mock_response = {
            "Rows": [
                {"Email": "test@example.com", "Name": "John Doe", "ID": "123"},
                {"Email": "another@example.com", "Name": "Jane Smith", "ID": "456"}
            ]
        }

        with patch.object(self.client, '_make_request', return_value=mock_response):
            result = self.client.find_items(table_name, item)
            self.assertEqual(len(result), 1)
            self.assertEqual(result[0]["Name"], item)

    def test_add_items(self):
        table_name = "Inventory Table"
        rows = [
            {
                "Generation Date": "1700000000",
                "UserID": "test@example.com",
                "Serial Number Hex": "ABC123",
                "SKU": "SKU123",
                "Batch": "Batch01",
            }
        ]

        mock_response = {"status": "OK"}

        with patch.object(self.client, '_make_request', return_value=mock_response):
            response = self.client.add_items(table_name, rows)
            self.assertEqual(response["status"], "OK")

    def test_edit_item(self):
        table_name = "Inventory Table"
        key_column = "Serial Number Hex"
        row_data = {
            "Serial Number Hex": "ABC123",
            "Bar Code": "Inventory_Images/ABC123_serial_barcode.svg",
            "QR Code": "Inventory_Images/ABC123_serial_qr.svg"
        }

        mock_response = {"status": "OK"}

        with patch.object(self.client, '_make_request', return_value=mock_response):
            response = self.client.edit_item(table_name, key_column, row_data)
            self.assertEqual(response["status"], "OK")

        def test_delete_row(self):
            table_name = "Inventory Table"
            key_column = "Serial Number Hex"
            key_value = "ABC123"

            mock_response = {"status": "OK"}

            with patch.object(self.client, '_make_request', return_value=mock_response):
                response = self.client.delete_row(table_name, key_column, key_value)
                self.assertEqual(response["status"], "OK")




if __name__ == '__main__':
    unittest.main()
