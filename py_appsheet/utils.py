def build_composite_key(*values, separator: str = ": ") -> str:
    """
    Build an AppSheet composite key matching the default _ComputedKey formula.

    AppSheet constructs composite keys using CONCATENATE([keycol1], ": ", [keycol2], ...)
    by default. Pass values in the same order as the key columns are defined in the table.

    Args:
        *values: The key column values, in key-column order.
        separator (str): The separator between values. Defaults to ": " to match AppSheet's default.

    Returns:
        str: The composite key string.

    Example:
        build_composite_key("foo", "bar")  # -> "foo: bar"
        build_composite_key("a", "b", "c")  # -> "a: b: c"
    """
    return separator.join(str(v) for v in values)


def build_selector(table_name: str, column: str, value: str, operator: str = "=") -> str:
    """
    Build an AppSheet selector expression for use with find_items().

    Constructs a Filter() expression that AppSheet evaluates server-side,
    avoiding the need to fetch and filter an entire table locally.

    Args:
        table_name (str): The AppSheet table name (must match exactly).
        column (str): The column name to filter on.
        value (str): The value to compare against.
        operator (str): The comparison operator. Defaults to "=".
            Common operators: "=", "!=", "<", ">", "<=", ">="

    Returns:
        str: An AppSheet selector expression string.

    Example:
        build_selector("Tasks", "Status", "In Progress")
        # -> "Filter(Tasks, [Status] = 'In Progress')"

        build_selector("Tasks", "Priority", "3", operator=">=")
        # -> "Filter(Tasks, [Priority] >= '3')"
    """
    return f"Filter({table_name}, [{column}] {operator} '{value}')"
