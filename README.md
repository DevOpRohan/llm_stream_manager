# LLM Stream Manager

A lightweight library for managing live token streams from LLMs.  Rules may drop, halt, or replace tokens on the fly and an optional history object keeps track of all processed tokens.

## Architecture

- `StreamManager` provides a minimal engine to apply rules.
- Rules consist of a keyword and a callback returning an `(Action, replacement)` tuple.
- `Action` supports: `PASS_TOKEN`, `DROP_TOKEN`, `REPLACE`, and `HALT`.
- Tokens are processed sequentially; the first matching rule determines the action.
- Async iterables are supported via :meth:`StreamManager.process_async`.
- A history of inputs, outputs and actions can optionally be recorded.

## Working

1. Instantiate `StreamManager`.
2. Register keywords with callbacks.
3. Feed any iterable of tokens to `StreamManager.process` and consume the resulting generator.

Callbacks inspect tokens containing their keyword and decide whether to pass, drop, replace, or halt the stream.

## Usage Example

```python
from llm_stream_manager import StreamManager, Action

manager = StreamManager(record_history=True)

# Drop tokens containing "secret"
manager.register("secret", lambda token: (Action.DROP_TOKEN, None))

# Replace tokens containing "foo" with "bar"
manager.register("foo", lambda token: (Action.REPLACE, token.replace("foo", "bar")))

source = ["hello", "secret code", "foo"]
for out in manager.process(source):
    print(out)
# Output: 'hello', 'bar'

# History of processing
print(manager.history.get_inputs())   # ['hello', 'secret code', 'foo']
```

### Async processing

```python
import asyncio

async def main():
    manager = StreamManager()
    manager.register("foo", lambda t: (Action.REPLACE, "bar"))
    async def source():
        for t in ["foo", "baz"]:
            yield t
    async for out in manager.process_async(source()):
        print(out)

asyncio.run(main())
```
