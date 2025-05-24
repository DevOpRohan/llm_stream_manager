import unittest

from streamfilter.core import KeywordRegistry, StreamProcessor, continuous_drop, replace
from streamfilter.integration import stream_filter


class TestHistoryFlagCore(unittest.TestCase):
    def test_disable_history_core(self):
        reg = KeywordRegistry()
        # Callback inspects history
        seen_enabled = []
        seen_disabled = []
        def cb_enabled(ctx):
            seen_enabled.append((ctx.history.get_inputs(), ctx.history.get_outputs(), ctx.history.get_actions()))
            return replace('X')
        def cb_disabled(ctx):
            seen_disabled.append((ctx.history.get_inputs(), ctx.history.get_outputs(), ctx.history.get_actions()))
            return replace('X')
        # Two registries to avoid mixing callbacks
        reg1 = KeywordRegistry()
        reg1.register('a', cb_enabled)
        reg2 = KeywordRegistry()
        reg2.register('a', cb_disabled)
        # Run with history enabled
        sp1 = StreamProcessor(reg1, record_history=True)
        for ch in 'ba': sp1.process(ch)
        sp1.flush()
        # history for 'a' should include ['b','a'] inputs, outputs/actions may be empty at match time
        inputs1, outputs1, actions1 = seen_enabled[0]
        self.assertEqual(inputs1, list('ba'))
        self.assertEqual(outputs1, [])
        self.assertTrue(isinstance(actions1, list))
        # Run with history disabled
        sp2 = StreamProcessor(reg2, record_history=False)
        for ch in 'ba': sp2.process(ch)
        sp2.flush()
        # history for 'a' should always be empty
        inputs2, outputs2, actions2 = seen_disabled[0]
        self.assertEqual(inputs2, [])
        self.assertEqual(outputs2, [])
        self.assertEqual(actions2, [])

class TestHistoryFlagIntegration(unittest.TestCase):
    def test_disable_history_decorator(self):
        reg = KeywordRegistry()
        seen = []
        def cb(ctx):
            seen.append((ctx.history.get_inputs(), ctx.history.get_outputs()))
            return continuous_drop()
        reg.register('X', cb)
        # Decorate with history disabled
        @stream_filter(reg, yield_mode='char', record_history=False)
        def src():
            yield 'bXc'
        # consume
        result = ''.join(src())
        # continuous_drop without pass marker drops following chars
        self.assertEqual(result, 'b')
        # callback saw empty histories
        for inputs, outputs in seen:
            self.assertEqual(inputs, [])
            self.assertEqual(outputs, [])

if __name__ == '__main__':
    unittest.main()