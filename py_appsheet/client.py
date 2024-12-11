#
import os
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

        """
        Find rows containing a specific item in the specified table.
        
        This method queries a table and retrieves rows containing the specified item.
        If the item corresponds to a unique key in the table, the returned row will
        contain all related data. For example, in an inventory table with columns like
        "serial number" (unique) and "registered", you might:
        
        - Query a specific serial number to find whether it is registered.
        - Query `True` to get all rows where "registered" is `True`.
        
        Args:
            table_name (str): The name of the table to search.
            item (Any): The value to search for in the table.

        Returns:
            list: A list of rows (dicts) containing the matching items. Returns an
                  empty list if no matching rows are found.
        """

    def find_items(self, table_name, item, target_column=None):
        """
        Find rows containing a specific item in the specified table.
        Optionally filter based on a specific column.
        Args:
            table_name (str): The name of the table to search. 
            Assumes only spaces as special characters (i.e. not &, ?, #)
            item (Any): The value to search for in the table.
            target_column (str, optional): The specific column to search in. If None,
                                        all columns are searched.

        Returns:
            list: A list of rows (dicts) containing the matching items. Returns an
                  empty list if no matching rows are found.
        """
        payload = {
            "Action": "Find",
            "Properties": {"Locale": "en-US", "Timezone": "UTC"},
            "Rows": [],
        }
        # Send the request
        response_data = self._make_request(table_name.replace(' ', '%20'), "Find", payload)

        # Error handling: Validate response format
        if not isinstance(response_data, list):
            raise ValueError("Unexpected response format: Expected a list of rows.")

        # Process response: Filter rows locally for matches
        if target_column:
            matching_rows = [row for row in response_data if row.get(target_column) == item]
        else:
            matching_rows = [row for row in response_data if item in row.values()]
        
        return matching_rows

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
            ValueError: If the response from the API is not in JSON format or contains an error.
        """
        payload = {
            "Action": "Add",
            "Properties": {
                "Locale": "en-US",
                "Timezone": "UTC"
            },
            "Rows": rows
        }

        # Encode table name for URL and send the request
        response_data = self._make_request(table_name.replace(' ', '%20'), "Add", payload)
    
        # Validate the response
        if not isinstance(response_data, dict):
            raise ValueError("Unexpected response format: Expected a JSON dictionary.")
    
        # Return the response
        return response_data

    def edit_item(self, table_name, key_column, row_data):
        """
        Edit a row in the specified AppSheet table.

        Args:
            table_name (str): The name of the table where the row exists.
            Assumes only spaces as special characters (i.e. not &, ?, #)
            key_column (str): The name of the key column in the table.
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

        # Encode table name for URL and send the request
        response_data = self._make_request(table_name.replace(' ', '%20'), "Edit", payload)

        # Validate the response
        if not isinstance(response_data, dict):
            raise ValueError("Unexpected response format: Expected a JSON dictionary.")

        return response_data

    def delete_row(self, table_name, key_column, key_value):
        """
        Delete a row in the specified AppSheet table.

        Args:
            table_name (str): The name of the table from which to delete the row.
            Assumes only spaces as special characters (i.e. not &, ?, #)
            key_column (str): The name of the key column in the table.
            key_value (Any): The value of the key column for the row to be deleted.

        Returns:
            dict: The response from the AppSheet API.

        Raises:
            ValueError: If the API response is not in JSON format or contains an error.
        """
        payload = {
            "Action": "Delete",
            "Properties": {
                "Locale": "en-US",
                "Timezone": "UTC"
            },
            "Rows": [
                {key_column: key_value}
            ]
        }

        # Encode table name for URL and send the request
        response_data = self._make_request(table_name.replace(' ', '%20'), "Delete", payload)

        # Validate the response
        if not isinstance(response_data, dict):
            raise ValueError("Unexpected response format: Expected a JSON dictionary.")

        return response_data




