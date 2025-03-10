# src/llm/pattern_detection/aho_corasick.py

"""Implements the Aho-Corasick string matching algorithm for pattern detection.

This module provides an implementation of the Aho-Corasick automaton, which enables
efficient multiple pattern string matching. The algorithm constructs a finite state
machine from a set of patterns and can find all occurrences of any pattern in a
given text in O(n + m + k) time, where n is the length of the text, m is the total
length of patterns, and k is the number of pattern occurrences.

Example:
    patterns = {'pattern1': 'abc', 'pattern2': 'def'}
    automaton = AhoCorasickAutomaton(patterns)
    matches = automaton.search_chunk('abcdef')
"""

from collections import deque
from typing import Dict, List, Tuple


class AhoCorasickAutomaton:
    """An implementation of the Aho-Corasick string matching automaton.

    This class implements a finite state machine that can efficiently match multiple
    patterns simultaneously in a given text. It uses a trie data structure augmented
    with failure links to achieve linear-time pattern matching.

    Attributes:
        patterns: A dictionary mapping pattern names to their string values.
        next_states: A list of dictionaries representing state transitions.
        fail: A list of failure link states.
        output: A list of pattern names associated with each state.
        current_state: The current state of the automaton.

    Args:
        patterns: A dictionary where keys are pattern names and values are the
            pattern strings to match.
    """

    def __init__(self, patterns: Dict[str, str]):
        """Initializes the Aho-Corasick automaton with the given patterns.

        Args:
            patterns: A dictionary mapping pattern names to their string values.
        """
        self.patterns = patterns
        self.next_states: List[Dict[str, int]] = []
        self.fail: List[int] = []
        self.output: List[List[str]] = []
        self.current_state = 0
        self._build_machine()

    def _build_machine(self):
        """Builds the Aho-Corasick automaton.

        Constructs the trie structure, sets up failure links, and computes output
        functions for the automaton. This is called automatically during initialization.
        """
        # Initialize root state
        self.next_states.append({})
        self.fail.append(0)
        self.output.append([])

        # Build the trie from patterns
        for pattern_name, pattern_str in self.patterns.items():
            self._insert(pattern_str, pattern_name)

        # Build failure links using BFS
        queue = deque()
        for char, nxt_state in self.next_states[0].items():
            self.fail[nxt_state] = 0
            queue.append(nxt_state)

        while queue:
            state = queue.popleft()
            for char, nxt_state in self.next_states[state].items():
                queue.append(nxt_state)
                f = self.fail[state]
                while f > 0 and char not in self.next_states[f]:
                    f = self.fail[f]
                f = self.next_states[f].get(char, 0)
                self.fail[nxt_state] = f
                self.output[nxt_state].extend(self.output[f])

    def _insert(self, pattern_str: str, pattern_name: str):
        """Inserts a pattern into the trie structure of the automaton.

         Args:
             pattern_str: The string pattern to insert.
             pattern_name: The name associated with the pattern.
         """
        current_state = 0
        for char in pattern_str:
            if char not in self.next_states[current_state]:
                self.next_states.append({})
                self.fail.append(0)
                self.output.append([])
                self.next_states[current_state][char] = len(self.next_states) - 1
            current_state = self.next_states[current_state][char]
        self.output[current_state].append(pattern_name)

    def reset_state(self):
        """Resets the automaton to its initial state.

        This method should be called before starting a new search if the automaton
        has been used previously.
        """
        self.current_state = 0

    def search_chunk(self, chunk: str) -> List[Tuple[int, str]]:
        """Searches for pattern matches in the given text chunk.

        Args:
            chunk: The text string to search for pattern matches.

        Returns:
            A list of tuples, where each tuple contains:
                - The ending index of the match in the chunk (int)
                - The name of the matched pattern (str)

        ``` python title="Example usage"
        automaton = AhoCorasickAutomaton({'pat1': 'abc', 'pat2': 'bc'})
        automaton.search_chunk('abc')  # [(1, 'pat2'), (2, 'pat1')]
        ```
        """
        found_patterns = []
        for i, char in enumerate(chunk):
            while self.current_state > 0 and char not in self.next_states[self.current_state]:
                self.current_state = self.fail[self.current_state]
            self.current_state = self.next_states[self.current_state].get(char, 0)
            if self.output[self.current_state]:
                for pattern_name in self.output[self.current_state]:
                    found_patterns.append((i, pattern_name))
        return found_patterns
