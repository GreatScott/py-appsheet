# py-appsheet
A no-frills Python library for interacting with the Google AppSheet API.

## Installation
```
pip install py-appsheet
```

## Setup

To use the AppSheet API you need an AppSheet **App** (not just an AppSheet Database).

1. Open your app and go to **Settings** (gear icon) → **Integrations**
2. Enable the API and note your **App ID**
3. Generate an **Application Access Key**

Store these as environment variables — never hardcode them:

```python
import os
from py_appsheet import AppSheetClient

client = AppSheetClient(
    app_id=os.environ.get("APPSHEET_APP_ID"),
    api_key=os.environ.get("APPSHEET_API_KEY"),
)
```

## Methods

### find_items — Read

Search a table for rows matching a value. Supports both local filtering (simple) and
server-side filtering via an AppSheet selector expression (efficient for large tables).

```python
# Return all rows in a table
rows = client.find_items("My Table")

# Filter by a specific column (local)
rows = client.find_items("My Table", "ABC123", target_column="Serial Number")

# Filter across all columns (local)
rows = client.find_items("My Table", "ABC123")

# Server-side filtering using an AppSheet selector expression (recommended for large tables)
from py_appsheet import build_selector

selector = build_selector("My Table", "Status", "In Progress")
rows = client.find_items("My Table", selector=selector)

# Combine: selector narrows server-side, then local filter refines further
rows = client.find_items("My Table", "Jane", target_column="Assignee", selector=selector)
```

### add_items — Create

Add one or more rows to a table.

```python
rows = [
    {"Title": "Task A", "Assignee": "Alice", "Status": "Not Started"},
    {"Title": "Task B", "Assignee": "Bob",   "Status": "In Progress"},
]

response = client.add_items("My Table", rows)
```

### edit_item — Update

Update an existing row. The key column must be included in `row_data`.

```python
response = client.edit_item(
    "My Table",
    "Serial Number",               # key column name
    {
        "Serial Number": "ABC123", # key column value (identifies the row)
        "Status": "Complete",      # fields to update
        "Notes": "Shipped",
    }
)
```

### delete_item — Delete

Delete a row by its key.

```python
# Single key column
response = client.delete_item("My Table", "Serial Number", "ABC123")

# Composite key: pass a dict of all key column values (see Composite Keys below)
response = client.delete_item("My Table", {"keycol1": "foo", "keycol2": "bar"})
```

`delete_row()` is available as a backwards-compatible alias for `delete_item()`.

---

## Composite Key Tables

When two or more columns are marked as keys in AppSheet, the app automatically creates
a computed key column (named `_ComputedKey` by default) whose value is the key columns
concatenated with `": "` as the separator.

Use `build_composite_key()` to construct the expected `_ComputedKey` value for filtering:

```python
from py_appsheet import build_composite_key

key = build_composite_key("foo", "bar")  # -> "foo: bar"

# Find a row by its computed key
rows = client.find_items("My Table", key, target_column="_ComputedKey")
```

For **edit** and **delete**, include all key columns directly in the row data — AppSheet
does not accept `_ComputedKey` in write payloads:

```python
# Edit: include all key columns + fields to update in row_data
client.edit_item(
    "My Table",
    "keycol1",                                           # any one key column goes first
    {"keycol1": "foo", "keycol2": "bar", "val": "new"}, # all key cols + updated fields
)

# Delete: pass a dict of all key column values
client.delete_item("My Table", {"keycol1": "foo", "keycol2": "bar"})
```

---

## Utilities

### build_selector

Constructs an AppSheet `Filter()` expression for use with `find_items()`.

```python
from py_appsheet import build_selector

build_selector("Tasks", "Status", "In Progress")
# -> "Filter(Tasks, [Status] = 'In Progress')"

build_selector("Tasks", "Priority", "3", operator=">=")
# -> "Filter(Tasks, [Priority] >= '3')"
```

### build_composite_key

Constructs a composite key string matching AppSheet's default `_ComputedKey` formula.

```python
from py_appsheet import build_composite_key

build_composite_key("foo", "bar")           # -> "foo: bar"
build_composite_key("a", "b", "c")          # -> "a: b: c"
build_composite_key("x", "y", separator="|") # -> "x|y"
```

---

## Troubleshooting

- **Schema out of date:** If you've added or changed columns in AppSheet, regenerate the
  schema in the app's Data view.
- **Key column errors:** Confirm your key column is marked correctly in AppSheet's column
  settings for that table.
- **Detailed error logs:** AppSheet → pulse icon → Monitor → Audit History → Launch Log Analyzer.
- **Table name encoding:** Table names may contain spaces (converted to `%20` automatically)
  but should not contain other URL special characters (`&`, `?`, `#`).

---

## Running Tests

**Unit tests** (no credentials needed):
```
pytest
```

**Integration tests** (requires a real AppSheet project):
```
pytest -m integration
```

Integration tests run against two specific tables. To set them up, create an AppSheet app
backed by a spreadsheet with the following tables:

**`example_table`**

| Column | Type | Key? |
|---|---|---|
| Title Example | Text | ✅ |
| Assignee | Text | |
| Status | Enum (`Not Started`, `In Progress`, `Complete`) | |
| Date | Date | |
| Another Column | Text | |

**`dual_key_table`**

| Column | Type | Key? |
|---|---|---|
| keycol1 | Text | ✅ |
| keycol2 | Text | ✅ |
| val | Text | |

> `_ComputedKey` is generated automatically by AppSheet when multiple key columns are present.

Add your App ID and access key to a `.env` file in the project root:
```
APP_ID=your-app-id
ACCESS_KEY=your-access-key
```

---

## Contributing
Contributions are welcome. Please submit pull requests to the `dev` branch.
