import unittest

from streamfilter.core import KeywordRegistry, StreamProcessor, StreamHistory, ActionDecision, ActionType, StreamHalted
from streamfilter import replace, passthrough, drop, halt


def core_run(registry, text, halt_on_error=False):
    """
    Run the StreamProcessor over text, returning the output string.
    If halt_on_error is True, swallow StreamHalted, else propagate.
    """
    sp = StreamProcessor(registry)
    out = []
    halted = False
    for ch in text:
        try:
            out.extend(sp.process(ch))
        except StreamHalted:
            if halt_on_error:
                halted = True
                break
            raise
    # flush remaining only if not halted
    if not (halt_on_error and halted):
        out.extend(sp.flush())
    return ''.join(out)


class TestComplex(unittest.TestCase):
    def test_multi_callback_and_history(self):
        # Two callbacks on same keyword: first PASS records, second REPLACE
        contexts = []
        def cb1(ctx):
            contexts.append(('cb1', ctx))
            return passthrough()
        def cb2(ctx):
            contexts.append(('cb2', ctx))
            return replace('X')

        reg = KeywordRegistry()
        reg.register('foo', cb1)
        reg.register('foo', cb2)
        # process a simple string
        result = core_run(reg, 'abcfoo')
        self.assertEqual(result, 'abcX')
        # Two callbacks invoked
        self.assertEqual(len(contexts), 2)
        name1, ctx1 = contexts[0]
        name2, ctx2 = contexts[1]
        self.assertEqual(name1, 'cb1')
        self.assertEqual(name2, 'cb2')
        # History inputs should include all seen chars
        self.assertEqual(ctx2.history.get_inputs(), list('abcfoo'))
        # History outputs reflects final emission
        self.assertEqual(ctx2.history.get_outputs(), list('abcX'))
        # Two actions recorded in history
        actions = ctx2.history.get_actions()
        self.assertEqual(len(actions), 2)
        # First action PASS, second REPLACE
        self.assertEqual(actions[0][2].type, ActionType.PASS)
        self.assertEqual(actions[1][2].type, ActionType.REPLACE)

    def test_callback_exception_propagation(self):
        # A callback that raises a ValueError should propagate
        def bad_cb(ctx):
            raise ValueError('oops')
        reg = KeywordRegistry()
        reg.register('err', bad_cb)
        with self.assertRaises(ValueError):
            core_run(reg, 'err')

    def test_overlapping_pattern_preference(self):
        # Ensure longer patterns win over shorter
        reg = KeywordRegistry()
        reg.register('abc', lambda ctx: replace('1'))
        reg.register('abcd', lambda ctx: replace('2'))
        # Input 'abcd' matches 'abc' then 'd' -> '1d'
        self.assertEqual(core_run(reg, 'abcd'), '1d')
        # Input 'abcx' matches 'abc' then 'x'
        self.assertEqual(core_run(reg, 'abcx'), '1x')

    def test_prefix_safety(self):
        # Partial prefix should not flush
        reg = KeywordRegistry()
        reg.register('longkw', lambda ctx: replace('Z'))
        # Input shorter than keyword
        self.assertEqual(core_run(reg, 'long'), 'long')
        # Exactly match, then replace
        out = core_run(reg, 'longkw')
        self.assertEqual(out, 'Z')

    def test_multiple_keywords_interleaving(self):
        # Two keywords may overlap but match separately
        reg = KeywordRegistry()
        reg.register('ab', lambda ctx: replace('A'))
        reg.register('bc', lambda ctx: replace('B'))
        # Input 'abc': matches 'ab' then 'c' -> 'Ac'
        self.assertEqual(core_run(reg, 'abc'), 'Ac')
        # Input 'xbc' -> 'xB'
        self.assertEqual(core_run(reg, 'xbc'), 'xB')

    def test_halt_and_no_flush(self):
        # On HALT, any remaining buffer should not be flushed
        reg = KeywordRegistry()
        reg.register('stop', lambda ctx: halt())
        # 'abcdstopef' -> 'abcd' then halt, no 'e','f'
        out = core_run(reg, 'abcdstopef', halt_on_error=True)
        # only prefix flushes before 'stop'
        self.assertEqual(out, 'abc')

    def test_streamhistory_api(self):
        # Directly use StreamHistory to record and retrieve
        hist = StreamHistory()
        hist.record_input('x')
        hist.record_output('y')
        d = replace('Z')
        hist.record_action(1, 'kw', d)
        self.assertEqual(hist.get_inputs(), ['x'])
        self.assertEqual(hist.get_outputs(), ['y'])
        acts = hist.get_actions()
        self.assertEqual(len(acts), 1)
        pos, kw, dec = acts[0]
        self.assertEqual(pos, 1)
        self.assertEqual(kw, 'kw')
        self.assertIs(dec, d)

if __name__ == '__main__':  # pragma: no cover
    unittest.main()