# ARCHITECTURE & DESIGN

## 1. The Real‑World Problem

Modern applications often embed LLMs into chatbots, assistants, or streaming interfaces.  As tokens arrive live:

- Sensitive content (PII, secrets) must be redacted or hidden.
- Marketing or formatting tokens may need replacement or injection.
- Certain terms should immediately abort the output (policy violations).
- Analytics events may be triggered on keywords.
- Segmented flows require dropping whole thought blocks and only displaying responses.

Engineering challenges:

- **Latency**: users expect sub‑millisecond per token throughput.
- **Safety**: no partial leakage of forbidden words (prefix‑safety).
- **Concurrency**: support both sync and async sources.
- **Extensibility**: allow dynamic rule updates at runtime.
- **Memory**: arbitrary history logging vs. resource constraints.

Without a robust framework, teams often resort to ad‑hoc solutions: regex in token loops, buffers with manual flush logic, complex state machines—becoming hard to maintain and error‑prone.

## 2. Technical Requirements

1. **Multi‑pattern detection**: up to 10k keywords, overlapping patterns.
2. **Prefix‑safe streaming**: no partial match emitted until keyword fully confirmed.
3. **Rich callbacks**: PASS, DROP, REPLACE(text), HALT, CONTINUE_DROP, CONTINUE_PASS.
4. **Pluggable history**: optional input/output/action logs per callback.
5. **Yield modes**: `'char'`, `'token'`, `'chunk:N'`.
6. **Minimal dependencies**: pure Python, standard library only.

## 3. Innovative Solution Overview

We built a **lazy, callback‑driven** streaming engine atop the classic **Aho–Corasick** multi-pattern matcher. Key innovations:

- **Lazy flush**: hold characters in a fixed‑size deque (max keyword length). Emit only when safe.
- **Longest‑match first**: resolve overlaps deterministically without backtracking.
- **Segment controls**: `CONTINUE_DROP` / `CONTINUE_PASS` enable dropping large segments between markers.
- **History toggle**: choose between full `StreamHistory` or a no-op stub (`_NullHistory`).
- **Decorator wrapper**: `@stream_filter` auto‑binds to sync/async generators with minimal code.

## 4. High‑Level Design

```text
Client Token Generator (sync/async)
            │
            ▼
   @stream_filter decorator layer
            │
            ▼
    StreamProcessor (AC + lazy flush + callbacks)
            │
            ▼
      Re-packer (char/token/chunk)
            │
            ▼
      Consumer (UI, logger, HTTP, etc.)
```

### 4.1 Decorator Layer

```python
@stream_filter(registry, yield_mode='token', record_history=True)
def my_generator():
    # yields LLM tokens
    yield from llm.stream()
```

- Detects sync vs. async generators
- Instantiates `StreamProcessor`
- Handles per-token flush in `'token'` mode
- Emits per-char or fixed‑chunk segments

## 5. Low‑Level Components

### 5.1 KeywordRegistry

- `register(keyword, callback)` / `deregister()`
- `compile()`: builds AC trie and failure links
- `max_len()`: longest keyword length

Data structure:
```python
class _Node:
    children: Dict[ch, _Node]
    fail: _Node
    output: List[(keyword, callbacks)]
```

### 5.2 StreamProcessor

Core per‑char method:
```python
def process(self, ch: str) -> List[str]:
    history.record_input(ch)
    buffer.append(ch)
    # AC state transition
    # On match: pick longest, run callbacks, apply decisions
    # Lazy flush: if buffer > max_len, pop left ↦ emit or drop
    return out_chars
```

- **AC traversal** with fail pointers for O(1) amortized per char
- **Decision engine** implements 6 ActionTypes
- **Drop mode** toggles full‑stream suppression
- **History** logs inputs/outputs/actions or uses no‑op stub

### 5.3 StreamHistory & _NullHistory

- Full history: lists of all seen/emitted chars and decisions
- NullHistory: stub that returns empty lists (zero memory)

## 6. Complexity Analysis

- **Time**: O(N + total matched callbacks)
- **Space**:
  - Trie: O(sum of keyword lengths)
  - Buffer: O(max keyword length)
  - History: O(N) if enabled, O(1) if disabled

## 7. Integration Guide

1. **Import**:
   ```python
   from streamfilter import KeywordRegistry, stream_filter
   ```
2. **Create registry, register callbacks**
3. **Apply decorator** to your LLM generator
4. **Consume** filtered output as needed

## 8. Extending & Embedding

- **Custom callbacks** can fire webhooks, update metrics, mutate external state.
- **Dynamic registry**: register/deregister at runtime; call `compile()` to rebuild trie.
- **Benchmark** with `bench.py` to choose optimal `record_history` flag for your workload.

---
By combining proven pattern‐matching with lazy buffering, callback flexibility, and minimal integration friction, `streamfilter` delivers a robust, high‐performance streaming sanitization framework for modern LLM applications.