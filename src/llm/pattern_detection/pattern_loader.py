# src/llm/streaming/pattern_loader.py

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