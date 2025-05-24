import unittest

from streamfilter.core import (
    KeywordRegistry,
    StreamProcessor,
    drop,
    replace,
    passthrough,
    halt,
    StreamHalted,
)


def run_processor(registry, text):
    """
    Helper to run a stream processor over input text and return the output string.
    """
    sp = StreamProcessor(registry)
    out_chars = []
    halted = False
    for ch in text:
        try:
            out_chars.extend(sp.process(ch))
        except StreamHalted:
            halted = True
            break
    if not halted:
        out_chars.extend(sp.flush())
    return ''.join(out_chars)


class TestCore(unittest.TestCase):
    def test_pass_through(self):
        reg = KeywordRegistry()
        text = 'The quick brown fox jumps over the lazy dog'
        self.assertEqual(run_processor(reg, text), text)

    def test_simple_replace(self):
        reg = KeywordRegistry()
        reg.register('secret', lambda ctx: replace('[REDACTED]'))
        inp = 'my secret data'
        exp = 'my [REDACTED] data'
        self.assertEqual(run_processor(reg, inp), exp)

    def test_drop(self):
        reg = KeywordRegistry()
        reg.register('foo', lambda ctx: drop())
        self.assertEqual(run_processor(reg, 'afoob'), 'ab')

    def test_halt(self):
        reg = KeywordRegistry()
        reg.register('stop', lambda ctx: halt())
        text = 'hello stop world'
        out = run_processor(reg, text)
        # should output only fully flushed characters before halt
        self.assertEqual(out, 'hello')

    def test_passthrough(self):
        reg = KeywordRegistry()
        reg.register('abc', lambda ctx: passthrough())
        self.assertEqual(run_processor(reg, 'xabcx'), 'xabcx')

    def test_longest_match_overlapping(self):
        reg = KeywordRegistry()
        reg.register('he', lambda ctx: replace('HE'))
        reg.register('she', lambda ctx: replace('SHE'))
        self.assertEqual(run_processor(reg, 'she'), 'SHE')

    def test_lazy_flush_and_replace(self):
        reg = KeywordRegistry()
        reg.register('abc', lambda ctx: replace('X'))
        inp = 'zabcq'
        self.assertEqual(run_processor(reg, inp), 'zXq')

    def test_dynamic_deregister(self):
        reg = KeywordRegistry()
        cb = lambda ctx: drop()
        reg.register('foo', cb)
        self.assertEqual(run_processor(reg, 'afoob'), 'ab')
        reg.deregister('foo', cb)
        self.assertEqual(run_processor(reg, 'afoob'), 'afoob')

    def test_max_len(self):
        reg = KeywordRegistry()
        reg.register('a', lambda ctx: passthrough())
        reg.register('abcd', lambda ctx: passthrough())
        self.assertEqual(reg.max_len(), 4)

    def test_register_after_compile(self):
        reg = KeywordRegistry()
        reg.register('foo', lambda ctx: passthrough())
        reg.compile()
        reg.register('bar', lambda ctx: passthrough())
        self.assertEqual(reg.max_len(), 3)
        self.assertEqual(run_processor(reg, 'barfoo'), 'barfoo')


if __name__ == '__main__':  # pragma: no cover
    unittest.main()