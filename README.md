# py-appsheet
A no-frills Python library for interacting with the Google AppSheet API. Depends only on [`requests`](https://requests.readthedocs.io) — no other third-party dependencies.

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

`locale` and `timezone` default to `"en-US"` and `"UTC"`. If AppSheet is misinterpreting date values, pass your local settings:

```python
client = AppSheetClient(
    app_id=os.environ.get("APPSHEET_APP_ID"),
    api_key=os.environ.get("APPSHEET_API_KEY"),
    locale="de-DE",
    timezone="Europe/Berlin",
)
```

## Export & Schema Workflow

Py-appsheet includes methods to help backup and export your tables and their schemas. The recommended workflow for exporting data safely:

**Step 1 — Infer the schema from live data:**
```python
# Single table
schema = client.infer_schema("Orders")

# Multiple tables at once — returns {table_name: schema}
schemas = client.infer_all_schemas(["Orders", "Patients", "Results"])
```
This fetches all rows, infers column types, and returns a schema dict with `contains_pii=False` on every column.

**Step 2 — Review and mark PII columns:**

Save the schema to a JSON file, edit it, and flip `contains_pii` to `true` for any columns that contain personal data. Optionally correct any type mismatches.

```json
{
  "Orders": {
    "columns": [
      {"name": "patient_name", "contains_pii": true,  "inferred_type": "string"},
      {"name": "order_ref",    "contains_pii": false, "inferred_type": "string"}
    ]
  }
}
```

**Step 3 — Export using the schema:**
```python
import json

with open("schemas.json") as f:
    schemas = json.load(f)

# Full export (emits a UserWarning if PII columns are present and not redacted)
data, log = client.export_all_tables(["Orders", "Patients"], schemas=schemas)

# De-identified export — PII columns replaced with "[REDACTED]"
data, log = client.export_all_tables(["Orders", "Patients"], schemas=schemas, redact_pii=True)
```

See `examples/export_workflow.py` for a complete runnable example.

> **Note:** Columns that are entirely blank across all rows may be omitted from the AppSheet API
> response and will be absent from the inferred schema. If your table has always-empty columns,
> add them manually to the schema JSON.

> **Note:** Redacted values are always replaced with the string `"[REDACTED]"` regardless of the
> column's original type (number, boolean, etc.). AppSheet returns all values as strings, so this
> is consistent with the data format throughout.

---

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

### update_item — Update

Update an existing row. The key column must be included in `row_data`.

```python
response = client.update_item(
    "My Table",
    "Serial Number",               # key column name
    {
        "Serial Number": "ABC123", # key column value (identifies the row)
        "Status": "Complete",      # fields to update
        "Notes": "Shipped",
    }
)
```

`edit_item()` is available as a backwards-compatible alias for `update_item()`.

### delete_item — Delete

Delete a row by its key.

```python
# Single key column
response = client.delete_item("My Table", "Serial Number", "ABC123")

# Composite key: pass a dict of all key column values (see Composite Keys below)
response = client.delete_item("My Table", {"keycol1": "foo", "keycol2": "bar"})
```

`delete_row()` is available as a backwards-compatible alias for `delete_item()`.

### export_table — Full table export

```python
# Export all rows
rows = client.export_table("Orders")

# With schema — ensures all schema columns present, even if blank in AppSheet
rows = client.export_table("Orders", schema=orders_schema)

# De-identified — PII columns replaced with "[REDACTED]"
rows = client.export_table("Orders", schema=orders_schema, redact_pii=True)
```

### export_all_tables — Multi-table export

```python
data, log = client.export_all_tables(
    ["Orders", "Patients"],
    schemas=schemas,      # dict of {table_name: schema}
    redact_pii=True,
)

# data -> {"Orders": [...rows...], "Patients": [...rows...]}
# log  -> {"status": "complete", "exported": [...], "failed": [...], ...}
```

Failed tables are logged and skipped — the export continues for remaining tables.

### infer_schema / infer_all_schemas — Data-driven schema inference

```python
# Single table
schema = client.infer_schema("Orders")

# Pass pre-fetched rows to avoid a redundant API call
rows = client.export_table("Orders")
schema = client.infer_schema("Orders", rows=rows)

# Multiple tables — returns {table_name: schema} ready for export_all_tables()
schemas = client.infer_all_schemas(["Orders", "Patients", "Results"])
```

### diff_schemas — Schema change detection

```python
from py_appsheet import diff_schemas

diff = diff_schemas(old_schema, new_schema)
# -> {"added": [...], "removed": [...], "type_changed": [...], "unchanged": [...]}
```

Works with schemas produced by `infer_schema()` or any user-provided schema dict containing a `columns` list with `name` and `inferred_type` (or `appsheet_type`) fields.

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
# Update: include all key columns + fields to update in row_data
client.update_item(
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
