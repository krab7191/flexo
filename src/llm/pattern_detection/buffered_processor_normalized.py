# src/llm/pattern_detection/buffered_processor_normalized.py

from src.data_models.streaming import PatternMatchResult
from src.llm.pattern_detection.pattern_utils import load_patterns
from src.llm.pattern_detection.pattern_utils import normalize_and_map
from src.llm.pattern_detection.base_buffered_processor import BaseBufferedProcessor
from src.llm.pattern_detection.aho_corasick_normalized import AhoCorasickAutomatonNormalized


class AhoCorasickBufferedProcessorNormalized(BaseBufferedProcessor):
    """A buffered processor that performs normalized pattern matching ignoring whitespace.

    This class implements pattern matching that is insensitive to whitespace variations
    by normalizing both patterns and input text. It uses the Aho-Corasick algorithm
    for efficient multiple pattern matching.

    Attributes:
        automaton: An instance of AhoCorasickAutomatonNormalized for pattern matching.
        max_pattern_len: The length of the longest pattern in the normalized patterns.
        tool_call_message: Message to include when a tool call is detected.

    Args:
        yaml_path: Path to the YAML file containing pattern definitions.
        tool_call_message: Optional message to use when a tool call is detected.
            Defaults to "Tool call detected."
    """

    def __init__(self, yaml_path: str, tool_call_message: str = "Tool call detected."):
        super().__init__(tool_call_message)
        raw_patterns = load_patterns(yaml_path)
        self.automaton = AhoCorasickAutomatonNormalized(raw_patterns)
        self.max_pattern_len = max(len(p) for p in self.automaton.normalized_patterns.values())
        self.automaton.reset_state()

    def process_chunk_impl(self, combined_original: str):
        """Processes a chunk of text to find pattern matches while ignoring whitespace.

        This method normalizes the input text, performs pattern matching, and returns
        the earliest match found along with any safe text that can be output.

        Args:
            `combined_original`: The original text chunk to process.

        Returns:
            A tuple containing:

                - `PatternMatchResult`: Result object containing match information and
                    processed text.
                - `str`: Any trailing text that needs to be carried over to the next
                    chunk.

        ``` python title="Example usage"
        processor = AhoCorasickBufferedProcessorNormalized('patterns.yaml')
        result, trailing = processor.process_chunk_impl('some text')
        print(result.matched, result.pattern_name)  # False None
        ```
        """
        result = PatternMatchResult()
        # Normalize the entire combined_original and get index mapping.
        norm_combined, index_map = normalize_and_map(combined_original)
        matches = self.automaton.search_chunk(norm_combined)

        if not matches:
            keep_len = min(self.max_pattern_len - 1, len(norm_combined))
            if keep_len > 0:
                orig_keep_start = index_map[len(norm_combined) - keep_len]
                safe_text = combined_original[:orig_keep_start]
                new_trailing = combined_original[orig_keep_start:]
            else:
                safe_text = combined_original
                new_trailing = ""
            result.output = safe_text
            return result, new_trailing

        # Find the earliest match
        earliest_original_index = None
        earliest_match_pattern = None
        earliest_norm_start_idx = None
        for norm_end_idx, pattern_name in matches:
            pat_len = self.automaton.get_pattern_length(pattern_name)
            norm_start_idx = norm_end_idx - pat_len + 1
            original_end = index_map[norm_end_idx]
            original_start = index_map[norm_start_idx]
            if earliest_original_index is None or original_end < earliest_original_index:
                earliest_original_index = original_end
                earliest_match_pattern = pattern_name
                earliest_norm_start_idx = norm_start_idx

        original_start = index_map[earliest_norm_start_idx]
        result.matched = True
        result.pattern_name = earliest_match_pattern
        result.tool_call_message = self.tool_call_message
        result.output = combined_original[:original_start]
        result.text_with_tool_call = combined_original[original_start:]
        new_trailing = ""
        self.automaton.reset_state()
        return result, new_trailing
