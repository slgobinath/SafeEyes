import unittest

from safeeyes.breaks.queue import Queue
from safeeyes.spi.breaks.spi import Break, BreakType


class QueueTestCase(unittest.TestCase):
    def test_seq_queue(self):
        queue = Queue(False)
        short_1 = Break(BreakType.SHORT, "short 1", 15, 15, None, [])
        short_2 = Break(BreakType.SHORT, "short 2", 15, 15, None, [])
        short_3 = Break(BreakType.SHORT, "short 3", 15, 15, None, [])
        short_4 = Break(BreakType.SHORT, "short 4", 15, 15, None, [])
        queue.add(short_1)
        queue.add(short_2)
        queue.add(short_3)
        queue.add(short_4)

        self.assertEqual(queue.is_empty(), False)
        self.assertEqual(queue.peek(), short_1)
        self.assertEqual(queue.next(), short_2)
        self.assertEqual(queue.next(), short_3)
        self.assertEqual(queue.peek(), short_3)
        self.assertEqual(queue.next(), short_4)
        self.assertEqual(queue.next(), short_1)

    def test_rand_queue(self):
        queue = Queue(True)
        short_1 = Break(BreakType.SHORT, "short 1", 15, 15, None, [])
        short_2 = Break(BreakType.SHORT, "short 2", 15, 15, None, [])
        short_3 = Break(BreakType.SHORT, "short 3", 15, 15, None, [])
        short_4 = Break(BreakType.SHORT, "short 4", 15, 15, None, [])
        queue.add(short_1)
        queue.add(short_2)
        queue.add(short_3)
        queue.add(short_4)

        first_batch = []
        second_batch = []
        self.assertEqual(queue.is_empty(), False)

        for _ in range(4):
            first_batch.append(queue.next().name)

        for _ in range(4):
            second_batch.append(queue.next().name)

        # Random order may have the same order. So this test may randomly fail
        self.assertNotEqual(first_batch, second_batch)

        first_batch = sorted(first_batch)
        second_batch = sorted(second_batch)
        self.assertEqual(first_batch, second_batch)


if __name__ == '__main__':
    unittest.main()
