import unittest

from streamfilter.core import KeywordRegistry, StreamProcessor
from streamfilter.core import continuous_drop, continuous_pass


def run_stream(reg, text):
    sp = StreamProcessor(reg)
    out = []
    for ch in text:
        try:
            out.extend(sp.process(ch))
        except Exception:
            break
    out.extend(sp.flush())
    return ''.join(out)


class TestSegmentControls(unittest.TestCase):
    def test_continuous_drop_and_pass(self):
        # Drop content between 'X' and 'Y'
        reg = KeywordRegistry()
        reg.register('X', lambda ctx: continuous_drop())
        reg.register('Y', lambda ctx: continuous_pass())
        inp = 'aX123Yb'
        # Expect 'a' before drop, then no '1','2','3', then 'Y' and 'b'
        # continuous_pass emits 'Y'
        out = run_stream(reg, inp)
        self.assertEqual(out, 'aYb')

    def test_nested_segments(self):
        # Support toggling multiple times
        reg = KeywordRegistry()
        reg.register('[', lambda ctx: continuous_drop())
        reg.register(']', lambda ctx: continuous_pass())
        inp = '1[23]4[56]7'
        # Should drop 23 and 56, emit markers and digits accordingly
        # continuous_pass emits ']' markers
        out = run_stream(reg, inp)
        # tokens: '1', drop '[23]', emit ']', '4', drop '[56]', emit ']', '7'
        self.assertEqual(out, '1]4]7')

    def test_no_initial_marker(self):
        # If pass mode by default, and continuous_pass before drop shouldn't break
        reg = KeywordRegistry()
        reg.register('Y', lambda ctx: continuous_pass())
        inp = 'abcYde'
        # All should pass; continuous_pass toggles but no drop
        out = run_stream(reg, inp)
        self.assertEqual(out, 'abcYde')

    def test_immediate_drop_marker(self):
        # If drop at first char
        reg = KeywordRegistry()
        reg.register('a', lambda ctx: continuous_drop())
        reg.register('c', lambda ctx: continuous_pass())
        inp = 'abc'
        # a: drop( entry ), state->drop, nothing emitted
        # b: drop
        # c: pass marker, should emit 'c'
        out = run_stream(reg, inp)
        self.assertEqual(out, 'c')
    def test_mixed_replace_and_segments(self):
        # Combine drop, replace, continuous_drop/pass
        from streamfilter.core import drop, replace
        reg = KeywordRegistry()
        reg.register('a', lambda ctx: drop())
        reg.register('b', lambda ctx: replace('X'))
        reg.register('c', lambda ctx: continuous_drop())
        reg.register('d', lambda ctx: continuous_pass())
        # Input: a b c d e
        # 'a' dropped, 'b'->'X', 'c' enters drop (flush X), 'd' emits marker, 'e' passes
        out = run_stream(reg, 'abcde')
        self.assertEqual(out, 'Xde')

class TestSegmentIntegration(unittest.TestCase):
    def test_sync_char_mode_segments(self):
        from streamfilter import stream_filter
        reg = KeywordRegistry()
        reg.register('X', lambda ctx: continuous_drop())
        reg.register('Y', lambda ctx: continuous_pass())
        @stream_filter(reg, yield_mode='char')
        def src():
            yield 'aX123Yb'
        self.assertEqual(''.join(src()), 'aYb')

    def test_sync_token_mode_segments(self):
        from streamfilter import stream_filter
        reg = KeywordRegistry()
        reg.register('X', lambda ctx: continuous_drop())
        reg.register('Y', lambda ctx: continuous_pass())
        @stream_filter(reg, yield_mode='token')
        def src():
            yield 'aX123Yb'
        # Single token processed to 'aYb' in token mode
        self.assertEqual(list(src()), ['aYb'])

    def test_async_char_mode_segments(self):
        import asyncio
        from streamfilter import stream_filter
        reg = KeywordRegistry()
        reg.register('x', lambda ctx: continuous_drop())
        reg.register('z', lambda ctx: continuous_pass())
        @stream_filter(reg, yield_mode='char')
        async def src():
            yield 'axxxzb'
        async def run():
            out = ''
            async for ch in src():
                out += ch
            return out
        result = asyncio.run(run())
        # drop between x and z
        self.assertEqual(result, 'azb')

if __name__ == '__main__':  # pragma: no cover
    unittest.main()