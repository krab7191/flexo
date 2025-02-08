# Pattern Detection Documentation

## Overview

The **Pattern Detection Module** provides utilities for detecting predefined patterns within text. The core implementation utilizes the **Aho-Corasick algorithm**, a fast and efficient string-searching algorithm.

## Components

### Aho-Corasick Automaton
- **`AhoCorasickAutomaton`** - A trie-based automaton for efficient multi-pattern searching.
- **`AhoCorasickBufferedProcessor`** - A buffered processor leveraging the Aho-Corasick algorithm for streaming text inputs.

## Performance Considerations

- The **Aho-Corasick algorithm** allows for **linear-time** searching, making it highly efficient for large-scale text processing.
- Buffered processing is **memory-efficient**, enabling real-time pattern detection in streaming applications.

## Additional Resources
- [LLM Module Overview](../index.md)
- [Tool Call Detection](../tool_detection/index.md)
