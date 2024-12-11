import os
from dotenv import load_dotenv
from py_appsheet.client import AppSheetClient

# Step 1: Load environment variables from .env file
load_dotenv()

APPSHEET_APP_ID = os.getenv("APPSHEET_APP_ID")
APPSHEET_API_KEY = os.getenv("APPSHEET_API_KEY")

if not APPSHEET_APP_ID or not APPSHEET_API_KEY:
    raise Exception("AppSheet App ID or API Key is missing. Check your .env file.")

# Step 2: Initialize the AppSheetClient
client = AppSheetClient(app_id=APPSHEET_APP_ID, api_key=APPSHEET_API_KEY)

# Step 3: Test table name and key column
TABLE_NAME = "Example Table Name Here"
KEY_COLUMN = "Title Example"

# Step 4: Add a new row to the table
print("Adding a new row...")
new_row = {
    "Title Example": "Test Row 1",
    "Another Column": "Value 1"
}

response = client.add_items(TABLE_NAME, [new_row])
print("Add response:", response)

input("\nPress Enter to continue to the next step...")

# Step 5: Find the newly added row
print("\nFinding the new row...")
find_response = client.find_items(TABLE_NAME, "Test Row 1", KEY_COLUMN)
print("Find response:", find_response)

input("\nPress Enter to continue to the next step...")

# Step 6: Edit the newly added row
print("\nEditing the new row...")
updated_row = {
    "Title Example": "Test Row 1",  # Must include the key column and its value
    "Another Column": "Updated Value"
}

edit_response = client.edit_item(TABLE_NAME, KEY_COLUMN, updated_row)
print("Edit response:", edit_response)

input("\nPress Enter to continue to the next step...")

# Step 7: Delete the row
print("\nDeleting the new row...")
delete_response = client.delete_row(TABLE_NAME, KEY_COLUMN, "Test Row 1")
print("Delete response:", delete_response)
