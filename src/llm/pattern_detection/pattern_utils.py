# src/llm/streaming/pattern_utils.py

import yaml
from typing import Dict


def load_patterns(yaml_path: str) -> Dict[str, str]:
    """
    Load tool call patterns from a YAML file.

    Args:
        yaml_path: Path to the YAML file containing patterns

    Returns:
        Dictionary mapping pattern names to pattern strings
    """
    with open(yaml_path, 'r') as f:
        config = yaml.safe_load(f)
    return config.get('patterns', {})


def normalize_and_map(text: str):
    """Returns a tuple of normalized text with whitespace removed and an index mapping.

    Processes the input text by removing all whitespace characters and creating
    a mapping that tracks the original position of each character.

    Args:
        text: The input string to be normalized.

    Returns:
        tuple: A tuple containing two elements:

            - `normalized_text` (str): The input text with all whitespace removed.
            - `index_map` (list): A list where index_map[i] is the original index
              of the i-th character in normalized_text.

    ``` python title="Example usage"
    normalize_and_map("a b c")  # ('abc', [0, 2, 4])
    ```
    """
    normalized_chars = []
    index_map = []
    for idx, ch in enumerate(text):
        if not ch.isspace():
            normalized_chars.append(ch)
            index_map.append(idx)
    return "".join(normalized_chars), index_map
