# tests/test_json_formatter.py

import pytest
from src.utils.json_formatter import format_json_to_document


def test_basic_structures():
    """Test basic data structure formatting"""
    # Simple dictionary
    assert format_json_to_document({"a": 1, "b": 2}) == "a: 1\nb: 2\n"

    # Simple list
    assert format_json_to_document([1, 2, 3]) == "0: 1\n1: 2\n2: 3\n"

    # Mixed types in dictionary
    result = format_json_to_document({
        "string": "text",
        "integer": 42,
        "float": 3.14,
        "boolean": True
    })
    assert "string: text\n" in result
    assert "integer: 42\n" in result
    assert "float: 3.14\n" in result
    assert "boolean: True\n" in result


def test_nested_structures():
    """Test nested data structure formatting"""
    test_data = {
        "person": {
            "name": "John Doe",
            "age": 30,
            "contact": {
                "email": "john@example.com",
                "phones": ["+1234567890", "+0987654321"]
            },
            "interests": ["reading", "hiking", {"sports": ["football", "tennis"]}],
            "metadata": None,
            "notes": "A very long note that should be truncated..." * 20,
            "empty_list": [],
            "empty_dict": {}
        }
    }

    formatted = format_json_to_document(
        test_data,
        indent_size=2,
        preview_length=50,
        max_length=100
    )

    # Test structure and indentation
    assert "person:\n" in formatted
    assert "  name: John Doe\n" in formatted
    assert "  contact:\n" in formatted
    assert "    email:" in formatted  # Test nested indentation
    assert "      0: +1234567890\n" in formatted  # Test list indentation


def test_edge_cases():
    """Test edge cases and special values"""
    # None values
    assert format_json_to_document(None) == "null\n"
    assert format_json_to_document({"key": None}) == "key: null\n"
    assert format_json_to_document([None, None]) == "0: null\n1: null\n"

    # Empty structures
    assert format_json_to_document({}) == "[empty]\n"
    assert format_json_to_document([]) == "[empty]\n"
    assert format_json_to_document({"empty": []}) == "empty: [empty]\n"

    # Nested empty structures
    assert "nested: [empty]\n" in format_json_to_document({"outer": {"nested": []}})

    # Special characters in strings
    special_chars = format_json_to_document({
        "newline": "hello\nworld",
        "tab": "hello\tworld",
        "unicode": "hello 🌍"
    })
    assert "newline: hello\nworld\n" in special_chars
    assert "tab: hello\tworld\n" in special_chars
    assert "unicode: hello 🌍\n" in special_chars


def test_formatting_options():
    """Test different formatting options"""
    data = {"a": [1, 2, {"b": 3}]}

    # Test indent size
    indent_result = format_json_to_document(data, indent_size=4)
    assert "    b: 3\n" in indent_result

    # Test without list indices
    no_indices = format_json_to_document(data, show_list_indices=False)
    assert "1\n" in no_indices
    assert "0: 1" not in no_indices

    # Test custom placeholders
    custom = format_json_to_document(
        {"a": None, "b": []},
        null_placeholder="NULL",
        empty_placeholder="EMPTY"
    )
    assert "a: NULL\n" in custom
    assert "b: EMPTY\n" in custom

    # Test truncation
    long_text = "x" * 200
    truncated = format_json_to_document(
        {"long": long_text},
        preview_length=10,
        max_length=20
    )
    assert "..." in truncated
    assert len(truncated.split("long: ")[1].strip()) < 15


def test_large_data_performance():
    """Test performance with large nested structures"""
    # Create a large nested structure
    large_data = {
        "level1": {
            f"key{i}": {
                f"subkey{j}": f"value{j}"
                for j in range(100)
            }
            for i in range(100)
        }
    }

    # Test performance and memory usage
    formatted = format_json_to_document(large_data)
    assert formatted.startswith("level1:\n")
    assert "key0:\n" in formatted
    assert "subkey0: value0\n" in formatted

    # Test with large lists
    large_list = list(range(10000))
    formatted_list = format_json_to_document(large_list)
    assert "0: 0\n" in formatted_list
    assert "9999: 9999\n" in formatted_list


def test_error_handling():
    """Test error handling and invalid inputs"""
    # Test with invalid indent size
    with pytest.raises(ValueError):
        format_json_to_document({}, indent_size=-1)

    # Test with invalid preview length
    with pytest.raises(ValueError):
        format_json_to_document({}, preview_length=0)

    # Test with circular reference
    d = {}
    d["self"] = d
    with pytest.raises(RecursionError):
        format_json_to_document(d)


if __name__ == "__main__":
    pytest.main([__file__])
