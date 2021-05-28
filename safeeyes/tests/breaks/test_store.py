import unittest

from safeeyes.breaks.store import BreaksStore
from safeeyes.config import Config
from safeeyes.context import Context
from safeeyes.util import locale


class BreaksStoreTestCase(unittest.TestCase):

    def test_breaks_store(self):
        ctx = Context(Config(), locale.init_locale())
        store = BreaksStore(ctx)

        batch = []

        self.assertEqual(store.is_empty(), False)
        for _ in range(20):
            batch.append(store.next())

        # Random order may have the same order. So this test may randomly fail
        for i in range(0, 20):
            if (i + 1) % 5 == 0:
                # Every 5th break is a long break
                self.assertTrue(batch[i].is_long_break())
            else:
                self.assertTrue(batch[i].is_short_break())


if __name__ == '__main__':
    unittest.main()
