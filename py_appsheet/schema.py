from __future__ import annotations

from datetime import datetime, timezone


def _infer_type(values: list) -> str:
    non_null = [v for v in values if v is not None and v != ""]
    if not non_null:
        return "unknown"
    if _all_match(non_null, _is_boolean):
        return "boolean"
    if _all_match(non_null, _is_integer):
        return "integer"
    if _all_match(non_null, _is_float):
        return "number"
    if _all_match(non_null, _is_datetime):
        return "datetime"
    return "string"


def _all_match(values: list, predicate) -> bool:
    return all(predicate(v) for v in values)


def _is_boolean(value: str) -> bool:
    return str(value).strip().lower() in ("true", "false")


def _is_integer(value: str) -> bool:
    try:
        int(str(value).strip())
        return True
    except ValueError:
        return False


def _is_float(value: str) -> bool:
    try:
        float(str(value).strip())
        return True
    except ValueError:
        return False


def _is_datetime(value: str) -> bool:
    formats = (
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
        "%m/%d/%Y",
        "%m/%d/%Y %H:%M:%S",
    )
    s = str(value).strip().rstrip("Z")
    for fmt in formats:
        try:
            datetime.strptime(s, fmt.rstrip("Z"))
            return True
        except ValueError:
            continue
    return False


class SchemaMixin:
    def infer_all_schemas(self, table_names: list[str]) -> dict[str, dict]:
        """
        Infer schemas for multiple tables.

        Args:
            table_names (list[str]): Names of tables to infer schemas for.

        Returns:
            dict[str, dict]: Schema dicts keyed by table name, ready to pass
                to export_all_tables(schemas=...).
        """
        return {table: self.infer_schema(table) for table in table_names}

    def infer_schema(
        self,
        table_name: str,
        rows: list[dict] | None = None,
    ) -> dict:
        """
        Infer a schema for the specified table from live API data.

        Args:
            table_name (str): The name of the table.
            rows (list[dict], optional): Pre-fetched rows to infer from. If None,
                fetches internally via export_table(). Pass pre-fetched rows to
                avoid a redundant API call when you already have the data.

        Returns:
            dict: A schema dict with source "data_inference". The contains_pii field
                defaults to False for all columns — set it manually as needed.
        """
        if rows is None:
            rows = self.export_table(table_name)

        column_names = []
        seen = set()
        for row in rows:
            for col in row:
                if col not in seen:
                    column_names.append(col)
                    seen.add(col)

        columns = []
        for col in column_names:
            values = [row.get(col) for row in rows]
            nullable = any(v is None or v == "" for v in values)
            columns.append({
                "name": col,
                "contains_pii": False,
                "inferred_type": _infer_type(values),
                "nullable": nullable,
            })

        return {
            "table_name": table_name,
            "appsheet_app_id": self.app_id,
            "captured_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "source": "data_inference",
            "row_count": len(rows),
            "columns": columns,
        }


def diff_schemas(old_schema: dict, new_schema: dict) -> dict:
    """
    Compare two schema dicts and return a summary of changes.

    Works with any schema source (data_inference, preview_scrape, manual).
    Uses inferred_type if present, otherwise appsheet_type for type comparison.

    Args:
        old_schema (dict): The previous schema.
        new_schema (dict): The current schema.

    Returns:
        dict: Keys: added, removed, type_changed, unchanged — each a list.
    """
    def col_map(schema):
        return {
            col["name"]: col.get("inferred_type") or col.get("appsheet_type")
            for col in schema.get("columns", [])
        }

    old = col_map(old_schema)
    new = col_map(new_schema)

    added = [name for name in new if name not in old]
    removed = [name for name in old if name not in new]
    type_changed = [
        {"column": name, "old_type": old[name], "new_type": new[name]}
        for name in old
        if name in new and old[name] != new[name]
    ]
    unchanged = [name for name in old if name in new and old[name] == new[name]]

    return {
        "added": added,
        "removed": removed,
        "type_changed": type_changed,
        "unchanged": unchanged,
    }
