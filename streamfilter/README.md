 # streamfilter

 > A callback-driven, prefix-safe, lazy LLM stream sanitizer with sync/async support.

 ## Overview

 `streamfilter` intercepts and sanitizes live token streams (e.g., from LLM SDKs) according to user-defined rules. It:

 - Redacts, drops, replaces, or halts on sensitive patterns.
 - Handles overlapping and multi-pattern matching efficiently via Aho–Corasick.
 - Supports sync and async token generators.
 - Offers per-keyword callback hooks with rich context and history.
 - Re-packets output in char, token, or fixed-size chunks.

 Low median overhead (~3µs per token on Apple M1) makes it suitable for real-time streaming.

 ## Quickstart (Code-First)

 Get up and running in 5 lines of code:

 ```python
 from streamfilter import KeywordRegistry, stream_filter, replace

 # 1. Create a registry and register a replacement rule
 reg = KeywordRegistry()
 reg.register("secret", lambda ctx: replace("[REDACTED]"))

 # 2. Decorate your token generator
 @stream_filter(reg, yield_mode='token')
 def gen():
     yield "The secret is 42 and the code is secret."

 # 3. Consume sanitized tokens
 print(list(gen()))  # ['The [REDACTED] is 42 and the code is [REDACTED].']
 ```

 ## Installation

 From PyPI (when released):

 ```bash
 pip install streamfilter
 ```

## Tutorial: Building a Live Stream Filter

Follow these steps to integrate `streamfilter` into your application:

1. Install the package
   ```bash
   pip install streamfilter
   ```
2. Import and create a `KeywordRegistry`
   ```python
   from streamfilter import KeywordRegistry, StreamProcessor, stream_filter
   reg = KeywordRegistry()
   ```
3. Define callback functions to drop, replace, pass, or halt on matches
   ```python
   from streamfilter.core import ActionType, ActionDecision

   def redact_secret(ctx):
       # Replace 'secret' with '[REDACTED]'
       return ActionDecision(ActionType.REPLACE, replacement='[REDACTED]')

   def abort_on_violence(ctx):
       # Halt stream on 'violence'
       return ActionDecision(ActionType.HALT)
   ```
4. Register your keywords and callbacks
   ```python
   reg.register('secret', redact_secret)
   reg.register('violence', abort_on_violence)
   ```
5. Wrap your generator (sync or async) with `@stream_filter`
   ```python
   @stream_filter(reg, yield_mode='char', record_history=True)
   def generate_tokens():
       # Example sync generator yielding tokens
       yield 'The secret '  
       yield 'is out.'
   ```
6. Consume the filtered stream
   ```python
   for out in generate_tokens():
       print(out, end='')
   ```
7. (Optional) Use `StreamProcessor` directly for fine-grained control:
   ```python
   sp = StreamProcessor(reg, record_history=False)
   output = ''
   for ch in 'my secret':
       output += ''.join(sp.process(ch))
   output += ''.join(sp.flush())
   print(output)  # 'my [REDACTED]'
   ```

 From source (development):

 ```bash
 git clone <repo>
 cd <repo>
 pip install -e .[dev]
 ```

 Dev requirements include pytest, mypy, and ruff.

 ## Core Concepts

 ### KeywordRegistry

 Register and manage keywords with callbacks:

 ```python
 from streamfilter.core import KeywordRegistry
 reg = KeywordRegistry()
 reg.register('secret', my_secret_callback)
 reg.deregister('secret', my_secret_callback)
 reg.compile()          # (optional; auto-compiled on demand)
 max_len = reg.max_len()  # longest keyword length
 ```

 ### StreamProcessor

 Low-level API that processes characters:

 ```python
 from streamfilter.core import StreamProcessor
 sp = StreamProcessor(reg)
 out_chars = []
 for ch in input_text:
     out_chars.extend(sp.process(ch))
 # flush any remaining
 out_chars.extend(sp.flush())
 result = ''.join(out_chars)
 ```

 ### ActionContext & ActionDecision

 Callbacks receive an `ActionContext` with:

 - `ctx.keyword`: matched keyword
 - `ctx.buffer`: list of chars currently buffered
 - `ctx.absolute_pos`: 1-based position in input
 - `ctx.history`: a `StreamHistory` object (see below)

 Callbacks must return an `ActionDecision(type, replacement=None)`:

 ```python
 from streamfilter.core import ActionType, ActionDecision
 # drop: remove keyword
 return ActionDecision(ActionType.DROP)
 # replace: remove keyword and insert text
 return ActionDecision(ActionType.REPLACE, replacement='[REDACTED]')
 # pass-through: do nothing
 return ActionDecision(ActionType.PASS)
 # halt stream: abort
 return ActionDecision(ActionType.HALT)
 ```

 Helper constructors:

 ```python
 from streamfilter.core import drop, replace, passthrough, halt
 # drop() == ActionDecision(ActionType.DROP)
 # replace('X') == ActionDecision(ActionType.REPLACE, replacement='X')
 # passthrough(), halt()
 ```

 ### StreamHistory

 Centralized history with query methods:

 ```python
 hist = ctx.history
 all_inputs = hist.get_inputs()      # list of all chars seen so far
 all_outputs = hist.get_outputs()    # list of all chars emitted so far
 all_actions = hist.get_actions()    # list of (pos, keyword, decision)
 ```

 ### Decorator Layer: `@stream_filter`

 Wrap any sync or async generator of string tokens:

 ```python
 from streamfilter import stream_filter, KeywordRegistry, replace, halt
 reg = KeywordRegistry()
 reg.register('foo', lambda ctx: replace('X'))
 reg.register('stop', lambda ctx: halt())

 @stream_filter(reg, yield_mode='token')
 def tokens():
     # e.g., yields LLM tokens
     yield 'foo'
     yield ' bar'
     yield ' stop'
     yield 'baz'

 for out in tokens():
     print(out)
 # prints: 'X', ' bar', then halts (no 'baz')
 ```

 Supported `yield_mode`:

 - `'char'`: yield individual characters
 - `'token'`: join and yield per-token strings
 - `'chunk:N'`: yield fixed-size chunks of N chars

 Sync and async generators are both supported; decorator auto-detects and wraps.

 ## Examples

 ### 1. Simple replacement

 ```python
 from streamfilter.core import KeywordRegistry, StreamProcessor
 from streamfilter import replace

 reg = KeywordRegistry()
 reg.register('secret', lambda ctx: replace('[REDACTED]'))
 sp = StreamProcessor(reg)

 text = 'My secret data.'
 out_chars = []
 for c in text:
     out_chars.extend(sp.process(c))
 out_chars.extend(sp.flush())
 result = ''.join(out_chars)
 print(result)
 # My [REDACTED] data.
 ```

 ### 2. Drop and halt behavior

 ```python
 from streamfilter import KeywordRegistry, StreamProcessor, drop, halt

 reg = KeywordRegistry()
 reg.register('foo', lambda ctx: drop())
 reg.register('stop', lambda ctx: halt())
 sp = StreamProcessor(reg)

 data = 'afoobstopxyz'
 out = ''
 for c in data:
     try:
         out += ''.join(sp.process(c))
     except:
         break
 out += ''.join(sp.flush())
 print(out)
 # ab
 ```

 ### 3. Sync decorator with chunks

 ```python
 from streamfilter import stream_filter, KeywordRegistry, replace
 reg = KeywordRegistry()
 reg.register('ab', lambda ctx: replace('Z'))

 @stream_filter(reg, yield_mode='chunk:2')
 def gen_tokens():
     yield 'a'
     yield 'bcd'

 print(list(gen_tokens()))
 # ['Z', 'cd']
 ```

 ### 4. Async generator with history

 ```python
 import asyncio
 from streamfilter import stream_filter, KeywordRegistry, replace

 reg = KeywordRegistry()
 reg.register('x', lambda ctx:
     replace(f"<{''.join(ctx.history.get_inputs())}>")
 )

 @stream_filter(reg, yield_mode='char')
 async def gen():
     yield 'abcx'

 async def main():
     out = ''
     async for ch in gen():
         out += ch
     print(out)
     # prints: '<abcx>'

 asyncio.run(main())
 ```

## Advanced Usage

### Continuous Drop/Pass Segments

Use `continuous_drop()` and `continuous_pass()` to drop or resume streaming segments:

```python
from streamfilter import KeywordRegistry, stream_filter
from streamfilter.core import continuous_drop, continuous_pass

reg = KeywordRegistry()
reg.register('<thought>', lambda ctx: continuous_drop())
reg.register('<response>', lambda ctx: continuous_pass())

@stream_filter(reg, yield_mode='token')
def chat_stream():
    # Simulated LLM output
    yield '<thought>This is hidden.</thought>'
    yield '<response>Hello, how can I help?</response>'
    yield '<thought>Another hidden thought</thought>'
    yield '<response>Continuing the response...</response>'

for tok in chat_stream():
    print(tok)
# Only <response> segments are shown; thoughts are dropped.
```

### Disabling History

To save memory, disable history tracking:

```python
from streamfilter.core import StreamProcessor

sp = StreamProcessor(reg, record_history=False)
# history data will be empty in callbacks
```

### Chunked Output

Aggregate characters into fixed-size chunks for downstream consumers:

```python
from streamfilter import stream_filter, KeywordRegistry

reg = KeywordRegistry()
# no transformations
@stream_filter(reg, yield_mode='chunk:5')
def source():
    yield 'abcdefghijklmnopqrstuvwxyz'

print(list(source()))
# ['abcde','fghij','klmno','pqrst','uvwxy','z']
```

 ## Testing & Benchmarking

 Run the test suite:

 ```bash
 pytest
 ```

 Benchmark throughput & memory:

```bash
python bench.py 5000000   # 5M characters
# sample output:
# record_history=True: 10.23 Mchars/s, peak memory=40.12 MB
# record_history=False: 12.45 Mchars/s, peak memory=2.01 MB
```

 ## Contributing

 - Fork the repo and open a PR.
 - Ensure tests pass and coverage remains at 100%.
 - Follow existing code style.

 ---

 Developed for TutorVideoAI compliance & UX streaming needs. Enjoy! 🚀