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
    """
    Returns (normalized_text, index_map), where:
      - normalized_text is 'text' with all whitespace removed.
      - index_map[i] = original index of the i-th character in normalized_text.
    """
    normalized_chars = []
    index_map = []
    for idx, ch in enumerate(text):
        if not ch.isspace():
            normalized_chars.append(ch)
            index_map.append(idx)
    return "".join(normalized_chars), index_map
