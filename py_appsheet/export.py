from __future__ import annotations

import warnings
from datetime import datetime, timezone


class ExportMixin:
    def export_table(
        self,
        table_name: str,
        schema: dict | None = None,
        redact_pii: bool = False,
    ) -> list[dict]:
        """
        Export all rows from the specified AppSheet table.

        Args:
            table_name (str): The name of the table to export.
            schema (dict, optional): A schema dict (from infer_schema(), the scraper, or manual).
                If provided, ensures every schema column is present in every row (filling None
                for columns AppSheet omitted). Also enables PII-aware behavior.
            redact_pii (bool): If True, replaces values in columns marked contains_pii=True
                with "[REDACTED]". Requires schema. Defaults to False.

        Returns:
            list[dict]: All rows from the table.

        Raises:
            ValueError: If redact_pii=True but no schema is provided.

        Note:
            Redacted values are always replaced with the string "[REDACTED]" regardless
            of the column's original type. AppSheet returns all values as strings, so
            this is consistent with the data format throughout.
        """
        if redact_pii and schema is None:
            raise ValueError("redact_pii=True requires a schema to identify PII columns.")

        rows = self.find_items(table_name)

        if schema is not None:
            columns = schema.get("columns", [])
            column_names = [col["name"] for col in columns]
            pii_columns = {col["name"] for col in columns if col.get("contains_pii", False)}

            if not redact_pii and pii_columns:
                warnings.warn(
                    f"Export of '{table_name}' includes columns marked contains_pii=True: "
                    f"{sorted(pii_columns)}. Pass redact_pii=True to redact them.",
                    UserWarning,
                    stacklevel=2,
                )

            normalized = []
            for row in rows:
                normalized_row = {col: row.get(col, None) for col in column_names}
                if redact_pii:
                    for col in pii_columns:
                        normalized_row[col] = "[REDACTED]"
                normalized.append(normalized_row)
            rows = normalized

        return rows

    def export_all_tables(
        self,
        table_names: list[str],
        schemas: dict[str, dict] | None = None,
        redact_pii: bool = False,
    ) -> tuple[dict[str, list[dict]], dict]:
        """
        Export multiple AppSheet tables.

        Args:
            table_names (list[str]): Names of tables to export.
            schemas (dict[str, dict], optional): A dict mapping table names to schema dicts.
                Tables not present in schemas are exported without a schema.
            redact_pii (bool): If True, redacts PII columns in all tables that have a schema.
                Defaults to False.

        Returns:
            tuple: (data, log)
                data (dict[str, list[dict]]): Successfully exported tables keyed by table name.
                log (dict): Export summary with status, timestamps, row counts, and any failures.
                    Status is "complete" if all tables succeeded, "partial" if any failed.
        """
        data = {}
        exported = []
        failed = []

        for table_name in table_names:
            schema = schemas.get(table_name) if schemas is not None else None
            table_redact_pii = redact_pii and schema is not None
            try:
                rows = self.export_table(table_name, schema=schema, redact_pii=table_redact_pii)
                data[table_name] = rows
                exported.append({"table": table_name, "row_count": len(rows)})
            except Exception as e:
                failed.append({"table": table_name, "error": str(e)})

        log = {
            "status": "complete" if not failed else "partial",
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "redact_pii": redact_pii,
            "exported": exported,
            "failed": failed,
        }

        return data, log
