import unittest
import asyncio

from streamfilter import KeywordRegistry, stream_filter, replace, halt


class TestIntegrationSync(unittest.TestCase):
    def test_sync_char_mode_basic(self):
        reg = KeywordRegistry()
        @stream_filter(reg, yield_mode='char')
        def src():
            yield 'hello '
            yield 'world'
        self.assertEqual(list(src()), list('hello world'))

    def test_sync_token_mode_basic(self):
        reg = KeywordRegistry()
        @stream_filter(reg, yield_mode='token')
        def src():
            yield 'hi'
            yield '!'
        self.assertEqual(list(src()), ['hi', '!'])

    def test_sync_chunk_mode(self):
        reg = KeywordRegistry()
        @stream_filter(reg, yield_mode='chunk:3')
        def src():
            yield 'abcdefgh'
        self.assertEqual(list(src()), ['abc', 'def', 'gh'])

    def test_cross_token_keyword(self):
        reg = KeywordRegistry()
        reg.register('ab', lambda ctx: replace('X'))
        @stream_filter(reg, yield_mode='char')
        def src():
            yield 'a'
            yield 'b'
        self.assertEqual(list(src()), ['X'])

    def test_sync_halt(self):
        reg = KeywordRegistry()
        reg.register('stop', lambda ctx: halt())
        @stream_filter(reg, yield_mode='char')
        def src():
            yield 'hello '
            yield 'stop'
            yield 'world'
        # only fully flushed characters before halt
        self.assertEqual(''.join(list(src())), 'he')

    def test_invalid_decorator_target(self):
        reg = KeywordRegistry()
        def not_gen():
            return 'oops'
        with self.assertRaises(TypeError):
            stream_filter(reg)(not_gen)

    def test_invalid_yield_mode(self):
        reg = KeywordRegistry()
        @stream_filter(reg, yield_mode='invalid')
        def src():
            yield 'a'
        with self.assertRaises(ValueError):
            list(src())


class TestIntegrationAsync(unittest.IsolatedAsyncioTestCase):
    async def test_async_char_mode(self):
        reg = KeywordRegistry()
        reg.register('x', lambda ctx: replace('Y'))
        @stream_filter(reg, yield_mode='char')
        async def src():
            yield 'abcxdef'
        out = []
        async for ch in src():
            out.append(ch)
        self.assertEqual(''.join(out), 'abcYdef')

if __name__ == '__main__':  # pragma: no cover
    unittest.main()