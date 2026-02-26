#
import requests

'''
Some notes:
- API Reference: https://support.google.com/appsheet/answer/10105398?sjid=1506075158107162628-NC
- Available actions: Add, Delete, Edit (requires lookup by table key), Find
- Table-names are passed in through URL, so if there are spaces in the name, %20 (percent-encoding)
  needs to be used
- Column-names are strings in the JSON payload and should not use %20 for representing spaces.
'''


class AppSheetClient:
    def __init__(self, app_id, api_key):
        self.app_id = app_id
        self.api_key = api_key

    def _make_request(self, table_name, action, payload):
        url = f"https://api.appsheet.com/api/v2/apps/{self.app_id}/tables/{table_name}/Action"
        headers = {
            "ApplicationAccessKey": self.api_key,
            "Content-Type": "application/json",
        }
        response = requests.post(url, json=payload, headers=headers)
        if response.status_code != 200:
            print(response)
            raise Exception(f"Request failed with status code {response.status_code}")
        return response.json()

    def find_items(self, table_name, item=None, target_column=None, selector=None):
        """
        Find rows in the specified AppSheet table.

        Supports two filtering modes:
        - Server-side: pass a `selector` string (AppSheet expression) for efficient API-level filtering.
        - Local: pass `item` (and optionally `target_column`) to filter the full table client-side.
        Both can be combined: selector narrows results server-side, then item/target_column refines locally.

        Args:
            table_name (str): The name of the table to search.
                Assumes only spaces as special characters (i.e. not &, ?, #)
            item (Any, optional): The value to search for. If None, all rows (or selector results) are returned.
            target_column (str, optional): The specific column to match `item` against.
                If None and item is set, all column values are searched.
            selector (str, optional): An AppSheet selector expression for server-side filtering,
                e.g. "Filter(MyTable, [Status] = 'Active')". Use utils.build_selector() to construct one.

        Returns:
            list: A list of rows (dicts) matching the criteria. Returns an empty list if no matches.
        """
        properties = {"Locale": "en-US", "Timezone": "UTC"}
        if selector:
            properties["Selector"] = selector

        payload = {
            "Action": "Find",
            "Properties": properties,
            "Rows": [],
        }

        response_data = self._make_request(table_name.replace(' ', '%20'), "Find", payload)

        if not isinstance(response_data, list):
            raise ValueError("Unexpected response format: Expected a list of rows.")

        if item is not None:
            if target_column:
                response_data = [row for row in response_data if row.get(target_column) == item]
            else:
                response_data = [row for row in response_data if item in row.values()]

        return response_data

    def add_items(self, table_name, rows):
        """
        Add one or more new rows to the specified AppSheet table.

        Args:
            table_name (str): The name of the table to which rows will be added.
                Assumes only spaces as special characters (i.e. not &, ?, #)
            rows (list[dict]): A list of dictionaries where each dictionary represents a row to be added.

        Returns:
            dict: The response from the AppSheet API.

        Raises:
            ValueError: If the response from the API is not in the expected format.
        """
        payload = {
            "Action": "Add",
            "Properties": {
                "Locale": "en-US",
                "Timezone": "UTC"
            },
            "Rows": rows
        }

        response_data = self._make_request(table_name.replace(' ', '%20'), "Add", payload)

        if not isinstance(response_data, dict):
            raise ValueError("Unexpected response format: Expected a JSON dictionary.")

        return response_data

    def edit_item(self, table_name, key_column, row_data):
        """
        Edit a row in the specified AppSheet table.

        Args:
            table_name (str): The name of the table where the row exists.
                Assumes only spaces as special characters (i.e. not &, ?, #)
            key_column (str): The name of the key column in the table.
                For composite-key tables, pass "_ComputedKey" (or the configured name)
                and include it in row_data using utils.build_composite_key().
            row_data (dict): A dictionary containing the data to update. The key
                             column and its value must be included.

        Returns:
            dict: The response from the AppSheet API.

        Raises:
            ValueError: If the key column is not present in `row_data`.
        """
        if key_column not in row_data:
            raise ValueError(f"The key column '{key_column}' must be included in the row data.")

        # Ensure the key column is the first dictionary entry
        row_data = {key_column: row_data[key_column], **{k: v for k, v in row_data.items() if k != key_column}}

        payload = {
            "Action": "Edit",
            "Properties": {
                "Locale": "en-US",
                "Timezone": "UTC"
            },
            "Rows": [row_data]
        }

        response_data = self._make_request(table_name.replace(' ', '%20'), "Edit", payload)

        if not isinstance(response_data, dict):
            raise ValueError("Unexpected response format: Expected a JSON dictionary.")

        return response_data

    def delete_item(self, table_name, key_column, key_value=None):
        """
        Delete a row in the specified AppSheet table.

        For single-key tables, pass the key column name and its value:
            delete_item("MyTable", "ID", "abc123")

        For composite-key tables, pass a dict of all key column values as key_column
        and omit key_value:
            delete_item("MyTable", {"keycol1": "v1", "keycol2": "v2"})

        Args:
            table_name (str): The name of the table from which to delete the row.
                Assumes only spaces as special characters (i.e. not &, ?, #)
            key_column (str | dict): The key column name (single key), or a dict mapping
                all key column names to their values (composite key).
            key_value (Any, optional): The value of the key column. Required when
                key_column is a string; omit when key_column is a dict.

        Returns:
            dict: The response from the AppSheet API.

        Raises:
            ValueError: If the API response is not in the expected format.
        """
        if isinstance(key_column, dict):
            row = key_column
        else:
            row = {key_column: key_value}

        payload = {
            "Action": "Delete",
            "Properties": {
                "Locale": "en-US",
                "Timezone": "UTC"
            },
            "Rows": [row]
        }

        response_data = self._make_request(table_name.replace(' ', '%20'), "Delete", payload)

        if not isinstance(response_data, dict):
            raise ValueError("Unexpected response format: Expected a JSON dictionary.")

        return response_data

    def delete_row(self, table_name, key_column, key_value):
        """Backwards-compatible alias for delete_item()."""
        return self.delete_item(table_name, key_column, key_value)
