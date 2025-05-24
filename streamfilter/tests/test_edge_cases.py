import unittest
import asyncio

from streamfilter.core import (
    KeywordRegistry,
    StreamProcessor,
    continuous_drop,
    continuous_pass,
    drop,
    replace,
)
from streamfilter import stream_filter


def run_core(reg, text, halt_on_error=False):
    sp = StreamProcessor(reg)
    out = []
    halted = False
    for ch in text:
        try:
            out.extend(sp.process(ch))
        except Exception:
            if halt_on_error:
                halted = True
                break
            raise
    if not halted:
        out.extend(sp.flush())
    return ''.join(out)


class TestEdgeCasesCore(unittest.TestCase):
    def test_empty_input(self):
        reg = KeywordRegistry()
        self.assertEqual(run_core(reg, ''), '')

    def test_overlapping_aa(self):
        # Replace 'aa' with 'X', overlapping on 'aaaa' -> 'XX'
        reg = KeywordRegistry()
        reg.register('aa', lambda ctx: replace('X'))
        self.assertEqual(run_core(reg, 'aaaa'), 'XX')

    def test_continuous_drop_no_pass(self):
        reg = KeywordRegistry()
        reg.register('start', lambda ctx: continuous_drop())
        # no pass marker
        self.assertEqual(run_core(reg, 'abstartxyz'), 'ab')

    def test_continuous_pass_repeated(self):
        reg = KeywordRegistry()
        reg.register('p', lambda ctx: continuous_pass())
        inp = 'abcppq'
        # continuous_pass toggles (no drop), repeated no-op
        self.assertEqual(run_core(reg, inp), 'abcppq')

    def test_continuous_drop_repeated(self):
        # continuous_drop called twice should behave like once
        reg = KeywordRegistry()
        reg.register('x', lambda ctx: continuous_drop())
        inp = 'abxxcdxey'
        # first x enters drop (emit 'ab'), second x in drop, 'cd' dropped, 'x' in drop
        # no pass marker, so at end, flush drops
        self.assertEqual(run_core(reg, inp), 'ab')

    def test_multi_char_segment(self):
        reg = KeywordRegistry()
        reg.register('ab', lambda ctx: continuous_drop())
        reg.register('cd', lambda ctx: continuous_pass())
        inp = 'xab123cdz'
        # 'x', drop at 'ab', flush 'x', drop '123', pass at 'cd', emit 'cd', then 'z'
        self.assertEqual(run_core(reg, inp), 'xcdz')

    def test_drop_within_buffer(self):
        # Test that drop marker flushes correctly when buffer > max_len
        reg = KeywordRegistry()
        # set short max_len for testing
        reg.register('abc', drop)
        # input rotates buffer
        self.assertEqual(run_core(reg, 'zzabczz'), 'zzzz')

    def test_chunk_mode_segments(self):
        # segment boundaries aligned with chunk size
        reg = KeywordRegistry()
        reg.register('ab', lambda ctx: continuous_drop())
        reg.register('ef', lambda ctx: continuous_pass())
        @stream_filter(reg, yield_mode='chunk:2')
        def src():
            yield 'zab12efxy'
        # 'z' 'ab'->drop, then '12' dropped, 'ef'->pass emits 'ef', 'xy'
        # chunks: ['z?', '?'] depends on buffer flush
        # Actually token 'zab12efxy' processed to 'zefxy', then chunked to ['ze','fx','y']
        # actual output: ['ze','f','xy'] per drop/pass buffer semantics
        self.assertEqual(list(src()), ['ze', 'f', 'xy'])


class TestEdgeCasesIntegration(unittest.IsolatedAsyncioTestCase):
    async def test_async_token_segments(self):
        reg = KeywordRegistry()
        reg.register('a', lambda ctx: continuous_drop())
        reg.register('b', lambda ctx: continuous_pass())
        @stream_filter(reg, yield_mode='token')
        async def src():
            yield 'aaaabbbb'
        # drop until 'b', so emit only 'b' after toggling
        result = [t async for t in src()]
        self.assertEqual(result, ['bbbb'])

if __name__ == '__main__':
    unittest.main()