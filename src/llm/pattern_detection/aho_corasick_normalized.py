# src/llm/pattern_detection/aho_corasick_normalized.py

"""Implements a normalized version of the Aho-Corasick string matching algorithm.

This module provides a wrapper around the base Aho-Corasick automaton that handles
text normalization for pattern matching. It normalizes patterns during initialization
and provides methods to search in normalized text.

Example:
    patterns = {'pattern1': 'hello world', 'pattern2': 'good bye'}
    automaton = AhoCorasickAutomatonNormalized(patterns)
    matches = automaton.search_chunk('hello    world')  # Matches despite extra spaces
"""

from typing import Dict, List, Tuple
from src.llm.pattern_detection.aho_corasick import AhoCorasickAutomaton
from src.llm.pattern_detection.pattern_utils import normalize_and_map


class AhoCorasickAutomatonNormalized:
    """A wrapper for normalized pattern matching using the Aho-Corasick algorithm.

    This class normalizes patterns by removing whitespace variations before building
    the underlying Aho-Corasick automaton. This allows for pattern matching that is
    insensitive to whitespace differences.

    Attributes:
        normalized_patterns: Dictionary mapping pattern names to their normalized forms.
        pattern_lengths: Dictionary storing the lengths of normalized patterns.
        automaton: The underlying AhoCorasickAutomaton instance.

    Args:
        patterns: Dictionary mapping pattern names to their original string patterns.
    """

    def __init__(self, patterns: Dict[str, str]):
        self.normalized_patterns = {}
        self.pattern_lengths = {}
        for name, pat in patterns.items():
            norm_pat, _ = normalize_and_map(pat)
            self.normalized_patterns[name] = norm_pat
            self.pattern_lengths[name] = len(norm_pat)

        self.automaton = AhoCorasickAutomaton(self.normalized_patterns)

    def reset_state(self):
        """Resets the automaton to its initial state.

        Should be called before starting a new search if the automaton has been
        used previously.
        """
        self.automaton.reset_state()

    def search_chunk(self, norm_chunk: str) -> List[Tuple[int, str]]:
        """Searches for pattern matches in normalized text.

        Args:
            norm_chunk: The normalized text chunk to search in. Should be
                pre-normalized before calling this method.

        Returns:
            A list of tuples, where each tuple contains:
                - The ending index of the match in the normalized text (int)
                - The name of the matched pattern (str)

        Example:
            >>> automaton = AhoCorasickAutomatonNormalized({'pat1': 'hello world'})
            >>> matches = automaton.search_chunk('helloworld')
            >>> print(len(matches))
            1
        """
        return self.automaton.search_chunk(norm_chunk)

    def get_pattern_length(self, pattern_name: str) -> int:
        """Returns the length of a normalized pattern.

        Args:
            pattern_name: The name of the pattern whose length is required.

        Returns:
            The length of the normalized pattern.

        Raises:
            KeyError: If the pattern_name is not found in the patterns dictionary.
        """
        return self.pattern_lengths[pattern_name]
