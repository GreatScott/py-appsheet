"""
Export workflow example.

Demonstrates the recommended approach for exporting AppSheet data with
schema-driven column normalization and optional PII redaction.

Step 1: Run with INFER=true to generate schemas.json for your tables.
Step 2: Edit schemas.json — set contains_pii=true on PII columns.
Step 3: Run normally to export using the saved schemas.

Usage:
    INFER=true python examples/export_workflow.py   # generate schemas.json
    python examples/export_workflow.py              # export with schemas
"""
import os
import json
from py_appsheet import AppSheetClient

client = AppSheetClient(
    app_id=os.environ["APPSHEET_APP_ID"],
    api_key=os.environ["APPSHEET_API_KEY"],
)

TABLE_NAMES = [
    "Orders",
    # "Patients",
]

SCHEMAS_FILE = "schemas.json"


def infer_and_save():
    schemas = client.infer_all_schemas(TABLE_NAMES)
    for table, schema in schemas.items():
        print(f"{table}: {len(schema['columns'])} columns, {schema['row_count']} rows")

    with open(SCHEMAS_FILE, "w") as f:
        json.dump(schemas, f, indent=2)

    print(f"\nSchemas saved to {SCHEMAS_FILE}")
    print("Review the file and set contains_pii=true on any PII columns, then re-run.")


def export_with_schemas():
    if not os.path.exists(SCHEMAS_FILE):
        raise FileNotFoundError(f"{SCHEMAS_FILE} not found — run with INFER=true first")

    with open(SCHEMAS_FILE) as f:
        schemas = json.load(f)

    data, log = client.export_all_tables(TABLE_NAMES, schemas=schemas, redact_pii=True)

    print(f"Status:    {log['status']}")
    print(f"Timestamp: {log['timestamp']}")
    print(f"Redacted:  {log['redact_pii_requested']}\n")

    for entry in log["exported"]:
        print(f"  {entry['table']}: {entry['row_count']} rows exported")

    for entry in log["failed"]:
        print(f"  FAILED: {entry['table']} — {entry['error']}")

    return data, log


if os.getenv("INFER"):
    infer_and_save()
else:
    data, log = export_with_schemas()
