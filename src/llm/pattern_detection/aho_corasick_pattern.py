# src/llm/streaming/aho_corasick_pattern.py

from collections import deque
from typing import Dict, List, Tuple

from src.llm.pattern_detection.pattern_loader import load_patterns
from src.data_models.streaming import PatternMatchResult


class AhoCorasickAutomaton:
    """Implements the Aho-Corasick string matching algorithm using a trie-based automaton.

    This class builds and maintains an Aho-Corasick automaton for efficient multiple
    pattern matching. It constructs a trie from the input patterns and augments it with
    failure links to enable simultaneous matching of multiple patterns in linear time.

    The automaton supports streaming pattern matching, maintaining its state between
    chunks of input text.

    Attributes:
        patterns (Dict[str, str]): Dictionary mapping pattern names to pattern strings.
        next_states (List[Dict[str, int]]): List of dictionaries representing state transitions.
            Each dictionary maps characters to next state indices.
        fail (List[int]): List of failure links for each state.
        output (List[List[str]]): List of pattern names that end at each state.
        current_state (int): Current state of the automaton for streaming matching.
    """

    def __init__(self, patterns: Dict[str, str]):
        """Initializes the Aho-Corasick automaton with the given patterns.

        Args:
            patterns: Dictionary mapping pattern names to their corresponding string patterns.
                Each pattern should be a non-empty string.
        """
        self.patterns = patterns
        self.next_states: List[Dict[str, int]] = []  # next_states[state] = {char: next_state}
        self.fail: List[int] = []  # fail[state] = fallback state
        self.output: List[List[str]] = []  # output[state] = list of pattern_names that end here
        self.current_state = 0  # Current state of the automaton (important for tracking state across streamed chunks)

        self._build_machine()

    def _build_machine(self):
        """Constructs the Aho-Corasick automaton in two phases.

        1. Builds a trie from all patterns
        2. Constructs failure links using breadth-first search
        """
        # Initialize root state
        self.next_states.append({})
        self.fail.append(0)
        self.output.append([])

        # Step 1: Build the trie
        for pattern_name, pattern_str in self.patterns.items():
            self._insert(pattern_str, pattern_name)

        # Step 2: Build the failure function using BFS
        queue = deque()

        # Initialize queue with depth-1 states (children of root)
        for char, nxt_state in self.next_states[0].items():
            self.fail[nxt_state] = 0  # Fail of a direct child of root is 0
            queue.append(nxt_state)

        # BFS to build fail links
        while queue:
            state = queue.popleft()

            # For each valid char from this state
            for char, nxt_state in self.next_states[state].items():
                queue.append(nxt_state)

                # Find the fail state for 'nxt_state'
                f = self.fail[state]
                while f > 0 and char not in self.next_states[f]:
                    f = self.fail[f]
                f = self.next_states[f].get(char, 0)
                self.fail[nxt_state] = f

                # Merge out patterns from the fail state
                self.output[nxt_state].extend(self.output[f])

    def _insert(self, pattern_str: str, pattern_name: str):
        """Inserts a single pattern into the trie structure.

        Args:
            pattern_str: The string pattern to insert.
            pattern_name: Name identifier for the pattern.
        """
        current_state = 0
        for char in pattern_str:
            if char not in self.next_states[current_state]:
                # Create a new state
                self.next_states.append({})
                self.fail.append(0)
                self.output.append([])
                self.next_states[current_state][char] = len(self.next_states) - 1
            current_state = self.next_states[current_state][char]
        # Mark that this state represents a complete pattern
        self.output[current_state].append(pattern_name)

    def reset_state(self):
        """Resets the automaton to its initial state."""
        self.current_state = 0

    def search_chunk(self, chunk: str) -> List[Tuple[int, str]]:
        """Processes a chunk of text and finds all pattern matches.

        Args:
            chunk: String of text to search for patterns.

        Returns:
            List of tuples (end_index, pattern_name) for each match found.
            The end_index indicates the position in the chunk where the pattern ends.
        """
        found_patterns = []

        for i, char in enumerate(chunk):
            # Follow fail links if mismatch
            while self.current_state > 0 and char not in self.next_states[self.current_state]:
                self.current_state = self.fail[self.current_state]

            # If there's a valid transition, advance; otherwise go to root (0)
            self.current_state = self.next_states[self.current_state].get(char, 0)

            # If output exists for the current state, report matches
            if self.output[self.current_state]:
                for pattern_name in self.output[self.current_state]:
                    found_patterns.append((i, pattern_name))

        return found_patterns


class AhoCorasickBufferedProcessor:
    """Provides a high-level interface for pattern matching using the Aho-Corasick algorithm.

    This class implements efficient pattern matching with smart buffer management to prevent
    pattern truncation across chunk boundaries while maintaining accuracy in streaming contexts.

    Args:
        yaml_path (str): Path to YAML file containing pattern definitions.
        tool_call_message (str, optional): Message to include when a tool call is detected.
            Defaults to "Tool call detected."

    Attributes:
        patterns (Dict[str, str]): Dictionary mapping pattern names to pattern strings.
        automaton (AhoCorasickAutomaton): The underlying Aho-Corasick automaton.
        tool_call_message (str): Message included with tool call detections.
        trailing_buffer (str): Buffer for handling text across chunk boundaries.
        max_pattern_len (int): Length of the longest pattern being matched.
    """

    def __init__(self, yaml_path: str, tool_call_message: str = "Tool call detected."):
        self.patterns = load_patterns(yaml_path)
        self.automaton = AhoCorasickAutomaton(self.patterns)
        self.tool_call_message = tool_call_message
        self.trailing_buffer = ""
        self.max_pattern_len = max(len(p) for p in self.patterns.values())

    def reset_states(self):
        """Resets all internal state.

        Clears the trailing buffer and resets the automaton to its initial state.
        Should be called between different processing sessions.
        """
        self.automaton.reset_state()
        self.trailing_buffer = ""

    async def process_chunk(self, chunk: str) -> PatternMatchResult:
        """Processes a chunk of text during streaming.

        Handles pattern matching while maintaining a buffer to prevent missing patterns
        that cross chunk boundaries. Manages partial matches and pattern detection
        across consecutive chunks.

        Args:
            chunk (str): Current chunk of text to process.

        Returns:
            PatternMatchResult: Result containing:

                - output: Processed text safe to yield
                - matched: Boolean indicating if a pattern was matched
                - pattern_name: Name of matched pattern if any
                - tool_call_message: Message about tool call if matched
                - text_with_tool_call: Text containing the tool call if matched
                - error: Any error message if processing failed

        Example:
            ```python
            processor = AhoCorasickBufferedProcessor("patterns.yaml")
            async for chunk in text_stream:
                result = await processor.process_chunk(chunk)
                if result.matched:
                    # Handle tool call
                if result.output:
                    # Yield processed text
            ```
        """
        result = PatternMatchResult()

        # Combine with any existing buffer
        combined_text = self.trailing_buffer + chunk

        # Find any complete matches
        matches = self.automaton.search_chunk(combined_text)

        if not matches:
            # Keep a buffer for potential patterns
            keep_len = min(self.max_pattern_len - 1, len(combined_text))
            result.output = combined_text[:-keep_len] if keep_len > 0 else combined_text
            self.trailing_buffer = combined_text[-keep_len:] if keep_len > 0 else ""
            return result

        # Handle match case
        earliest_match_index, matched_pattern = min(matches, key=lambda x: x[0])
        pattern_str = self.patterns[matched_pattern]
        match_start = earliest_match_index - len(pattern_str) + 1

        # Populate the result
        result.matched = True
        result.pattern_name = matched_pattern
        result.tool_call_message = self.tool_call_message
        result.output = combined_text[:match_start]
        result.text_with_tool_call = combined_text[match_start:]

        # Clear the buffer since we found a match
        self.trailing_buffer = ""

        return result

    async def flush_buffer(self) -> PatternMatchResult:
        """Flushes any remaining content in the trailing buffer.

        Should be called at the end of streaming to ensure no content remains
        buffered. This method handles the final state of the streaming process
        by releasing any remaining buffered content.

        Returns:
            PatternMatchResult: Result containing any remaining buffered content in
                the output field. Other fields will be empty/default values.

        Example:
            ```python
            processor = AhoCorasickBufferedProcessor("patterns.yaml")
            # ... process chunks ...
            final_result = await processor.flush_buffer()
            if final_result.output:
                # Handle final buffered content
            ```
        """
        result = PatternMatchResult()
        if self.trailing_buffer:
            result.output = self.trailing_buffer
            self.trailing_buffer = ""
        return result
