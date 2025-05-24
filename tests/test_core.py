import asyncio
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from llm_stream_manager import StreamManager, Action, StreamHistory


def test_basic_replace_and_drop():
    manager = StreamManager(record_history=True)
    manager.register('foo', lambda t: (Action.REPLACE, 'bar'))
    manager.register('bad', lambda t: (Action.DROP_TOKEN, None))
    source = ['foo', 'ok', 'bad', 'end']
    out = list(manager.process(source))
    assert out == ['bar', 'ok', 'end']
    # history recorded
    assert manager.history.get_inputs() == source
    assert manager.history.get_outputs() == ['bar', 'ok', 'end']


def test_deregister():
    manager = StreamManager()
    cb = lambda t: (Action.DROP_TOKEN, None)
    manager.register('x', cb)
    manager.deregister('x', cb)
    out = list(manager.process(['x']))
    assert out == ['x']


def test_process_async():
    async def run():
        manager = StreamManager()
        manager.register('foo', lambda t: (Action.REPLACE, 'bar'))

        async def source():
            for t in ['foo', 'baz']:
                yield t

        res = []
        async for tok in manager.process_async(source()):
            res.append(tok)
        return res

    result = asyncio.run(run())
    assert result == ['bar', 'baz']

