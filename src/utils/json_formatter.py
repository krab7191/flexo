# src/utils/json_formatter.py

from typing import Any, Dict, Union, Iterator


def _truncate_value(value: str, preview_length: int, max_length: int) -> str:
    """Truncate long string values with ellipsis.

    Args:
        value (str): String to truncate.
        preview_length (int): Length of preview before truncation.
        max_length (int): Maximum allowed length.

    Returns:
        str: Truncated string if needed, original string otherwise.
    """
    if len(value) > max_length:
        return value[:preview_length] + "..."
    return value


def format_json_to_document(
        data: Union[Dict[str, Any], list, None],
        level: int = 0,
        indent_size: int = 1,
        preview_length: int = 100,
        max_length: int = 500,
        show_list_indices: bool = True,
        null_placeholder: str = "null",
        empty_placeholder: str = "[empty]"
) -> str:
    """Format JSON-like data into a readable document string.

    Converts complex nested data structures into a human-readable
    formatted string with proper indentation and value truncation.

    Args:
        data: Data structure to format (dict, list, or None).
        level: Starting indentation level.
        indent_size: Number of spaces per indent level.
        preview_length: Length of preview for truncated values.
        max_length: Maximum length before truncation.
        show_list_indices: Whether to show indices in lists.
        null_placeholder: String to use for None values.
        empty_placeholder: String to use for empty collections.

    Returns:
        str: Formatted string representation of the data.

    Raises:
        ValueError: If indent_size, preview_length, or max_length are invalid.
        RecursionError: If data contains circular references.

    Example:
        ```python
        data = {
            "name": "example",
            "values": [1, 2, 3],
            "nested": {"key": "value"}
        }
        formatted = format_json_to_document(
            data,
            indent_size=2,
            show_list_indices=True
        )
        ```
    """
    if indent_size < 1:
        raise ValueError("indent_size must be positive")
    if preview_length < 1:
        raise ValueError("preview_length must be positive")
    if max_length <= preview_length:
        raise ValueError("max_length must be greater than preview_length")

    def _format_recursive(obj: Any, current_level: int) -> Iterator[str]:
        indent = " " * current_level

        # Handle None case
        if obj is None:
            yield f"{indent}{null_placeholder}\n"
            return

        # Handle empty collections at the top level
        if isinstance(obj, (list, dict)) and not obj:
            yield f"{indent}{empty_placeholder}\n"
            return

        # Handle list case
        if isinstance(obj, list):
            for i, item in enumerate(obj):
                if item is None:  # Handle None in lists
                    prefix = f"{i}: " if show_list_indices else ""
                    yield f"{indent}{prefix}{null_placeholder}\n"
                elif isinstance(item, (dict, list)):
                    if show_list_indices:
                        yield f"{indent}{i}:\n"
                    if not item:  # Empty nested collection
                        yield f"{' ' * (current_level + indent_size)}{empty_placeholder}\n"
                    else:
                        yield from _format_recursive(item, current_level + indent_size)
                else:
                    prefix = f"{i}: " if show_list_indices else ""
                    truncated = _truncate_value(str(item), preview_length, max_length)
                    yield f"{indent}{prefix}{truncated}\n"
            return

        # Handle dict case
        if isinstance(obj, dict):
            for key, value in obj.items():
                if value is None:
                    yield f"{indent}{key}: {null_placeholder}\n"
                elif isinstance(value, (dict, list)):
                    if not value:  # Empty nested collection
                        yield f"{indent}{key}: {empty_placeholder}\n"
                    else:
                        yield f"{indent}{key}:\n"
                        yield from _format_recursive(value, current_level + indent_size)
                else:
                    truncated = _truncate_value(str(value), preview_length, max_length)
                    yield f"{indent}{key}: {truncated}\n"
            return

        # Handle primitive value case
        yield f"{indent}{str(data)}\n"

    return "".join(_format_recursive(data, level))
