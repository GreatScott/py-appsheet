# py-appsheet
A no-frills Python library for interacting with Google AppSheet

## Background and Setup
* To work with this you need to create an AppSheet App first (i.e. not just an AppSheet Database). 
* To enable working with the API, you must go into the app's settings (gear icon) and then the integrations sub-item on the left. There you will find the App ID (make sure it's switched to enabled) and can create an Application Access key.
* Be sure to not write these explicitly into your code. Instead it's better to store these in a .env file (make sure .gitignore lists the .env if working with a repo) and use `os.environ.get()` to pull in the secret values to work with them.
* Some basic troubleshooting tips:
	* Make sure that you have your key column set correctly and that your schema is up-to-date (can be regenerated in the data view for the application)
	* Leverage Appsheet's Log Analyzer to get in-depth error messages. Can be access under your Appsheet App -> icon that looks like a pulse -> "Monitor" submenu -> "Audit History" -> "Launch log analyzer"



## Available Methods

### Find Items
1. Search for a Specific Value in Any Column
`result = client.find_item("Table Name", "ABC123")
`
2. Search for a Specific Vaue in a Specific Column
`result = client.find_item("Table Name", "ABC123", target_column="column name")`

### Add Items (New Rows)

```
rows_to_add = [
    {
        "Generation Date": "1700000000",
        "UserID": "someone@someone.com",
        "Serial Number Hex": "ABC123",
        "SKU": "SKU123",
        "Batch": "Batch01",
    },
    {
        "Generation Date": "1700000001",
        "UserID": "john@doe.com",
        "Serial Number Hex": "DEF456",
        "SKU": "SKU456",
        "Batch": "Batch02",
    }
]


# Add rows to the AppSheet table
response = client.add_item("Inventory Table", rows_to_add)

# Process the response
print("Response from AppSheet API:", response)


```

### Edit Item

Note: when updating an entry, the dictionary's first entry in the row data should be the designated key column (as defined in the AppSheet app settings for that table)

```
# Example usage of edit_item
serial_number = "ABC123"
sku = "SKU456"

row_data = {
    "Serial Number Hex": serial_number,  # Key column for the table
    "Bar Code": f"Inventory_Images/{serial_number}_serial_barcode.svg",
    "QR Code": f"Inventory_Images/{serial_number}_serial_qr.svg",
    "SKU Bar Code": f"Inventory_Images/{sku}_sku_barcode.svg"
}

response = client.edit_item("Inventory Table", "Serial Number Hex", row_data)

if response.get("status") == "OK":
    print("Row updated successfully with image paths.")
else:
    print(f"Failed to update row. API response: {response}")

```

### Delete Row by Key

```
# Example: Delete a row by its key
# "Serial Number Hex" is key col name

response = client.delete_row("Inventory Table", "Serial Number Hex", "ABC123") 

```


## Known Limitations and Important Notes
*(Contributions Welcome!)*

* Querying for specific rows that contain an item of interest currently pulls all rows and filters locally.
* Finding items currently pulls all rows and returns it in whatever, but the API does appear to have support for filtering and ordering. [See here](https://support.google.com/appsheet/answer/10105770?hl=en&ref_topic=10105767&sjid=1506075158107162628-NC)
* Appsheet table names, which are used in URL-encoding, are assumed to not contain any special characters other than spaces. I.e. you can supply a table name like `"my table"` and the library will convert this to `"my%20table"` as needed under the hood, but does not handle other special characters that may mess with URL-encoding. 

## Additional Credits
Credit where credit is due. ChatGPT was leveraged extensively to put this together quickly. 

## Contributing
Contributions are welcome. Please submit pull requests to the dev branch.