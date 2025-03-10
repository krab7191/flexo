# src/llm/pattern_detection/buffered_processor_standard.py

from src.data_models.streaming import PatternMatchResult
from src.llm.pattern_detection.pattern_utils import load_patterns
from src.llm.pattern_detection.aho_corasick import AhoCorasickAutomaton
from src.llm.pattern_detection.base_buffered_processor import BaseBufferedProcessor


class AhoCorasickBufferedProcessor(BaseBufferedProcessor):
    """A buffered processor that performs exact pattern matching.

    This class implements exact pattern matching using the Aho-Corasick algorithm
    for efficient multiple pattern matching. Unlike the normalized version, this
    processor is sensitive to whitespace and performs exact string matching.

    Attributes:
        `automaton`: An instance of AhoCorasickAutomaton for pattern matching.
        `max_pattern_len`: The length of the longest pattern in the raw patterns.
        `tool_call_message`: Message to include when a tool call is detected.

    Args:
        `yaml_path`: Path to the YAML file containing pattern definitions.
        `tool_call_message`: Optional message to use when a tool call is detected.
            Defaults to "Tool call detected."
    """

    def __init__(self, yaml_path: str, tool_call_message: str = "Tool call detected."):
        super().__init__(tool_call_message)
        raw_patterns = load_patterns(yaml_path)
        self.automaton = AhoCorasickAutomaton(raw_patterns)
        self.max_pattern_len = max(len(p) for p in raw_patterns.values())
        self.automaton.reset_state()

    def process_chunk_impl(self, combined_original: str):
        """Processes a chunk of text to find exact pattern matches.

        This method performs exact pattern matching on the input text and returns
        the earliest match found along with any safe text that can be output.

        Args:
            `combined_original`: The text chunk to process.

        Returns:
            A tuple containing:

                - `PatternMatchResult`: Result object containing match information and
                    processed text.
                - `str`: Any trailing text that needs to be carried over to the next
                    chunk.

        ``` python title="Example usage"
        processor = AhoCorasickBufferedProcessor('patterns.yaml')
        result, trailing = processor.process_chunk_impl('some text')
        print(result.matched, result.pattern_name)  # False None
        ```
        """
        result = PatternMatchResult()
        # Search in the original text
        matches = self.automaton.search_chunk(combined_original)

        if not matches:
            # Keep up to max_pattern_len - 1 characters for partial match
            keep_len = min(self.max_pattern_len - 1, len(combined_original))
            if keep_len > 0:
                safe_text = combined_original[:-keep_len]
                new_trailing = combined_original[-keep_len:]
            else:
                safe_text = combined_original
                new_trailing = ""
            result.output = safe_text
            return result, new_trailing

        # Otherwise, use the earliest match
        earliest_end, pattern_name = min(matches, key=lambda x: x[0])
        pattern_str = self.automaton.patterns[pattern_name]
        match_start = earliest_end - len(pattern_str) + 1

        result.matched = True
        result.pattern_name = pattern_name
        result.tool_call_message = self.tool_call_message
        result.output = combined_original[:match_start]
        result.text_with_tool_call = combined_original[match_start:]
        new_trailing = ""
        self.automaton.reset_state()
        return result, new_trailing
