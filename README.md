# LLM Stream Manager

A lightweight library for managing live token streams from LLMs. It allows registering simple keyword rules that can drop, halt, or replace tokens on the fly.

## Architecture

- `StreamManager` provides a minimal engine to apply rules.
- Rules consist of a keyword and a callback returning an `(Action, replacement)` tuple.
- `Action` supports: `PASS_TOKEN`, `DROP_TOKEN`, `REPLACE`, and `HALT`.
- Tokens are processed sequentially; the first matching rule determines the action.

## Working

1. Instantiate `StreamManager`.
2. Register keywords with callbacks.
3. Feed any iterable of tokens to `StreamManager.process` and consume the resulting generator.

Callbacks inspect tokens containing their keyword and decide whether to pass, drop, replace, or halt the stream.

## Usage Example

```python
from llm_stream_manager import StreamManager, Action

manager = StreamManager()

# Drop tokens containing "secret"
manager.register("secret", lambda token: (Action.DROP_TOKEN, None))

# Replace tokens containing "foo" with "bar"
manager.register("foo", lambda token: (Action.REPLACE, token.replace("foo", "bar")))

source = ["hello", "secret code", "foo"]
for out in manager.process(source):
    print(out)
# Output: 'hello', 'bar'
```
