import unittest

from bdd_coder import stock


class SetPairTests(unittest.TestCase):
    pairs = (stock.SetPair([1, 2], [3, 8]),
             stock.SetPair([1, '2'], ['2', 1]),
             stock.SetPair([1, 2, 3], [3, 2, 'A', 1.41]),
             stock.SetPair([2, 'K'], ['K', 2, 8, 1]),
             stock.SetPair([(2,), 5, 3], [3, (2,)]))

    def test_str(self):
        assert tuple(map(str, self.pairs)) == (
            'l ⪥ r: {1, 2} | ø | {3, 8}',
            "l = r: ø | {'2', 1} | ø",
            "l ⪤ r: {1} | {2, 3} | {'A', 1.41}",
            "l ⊂ r: ø | {'K', 2} | {1, 8}",
            'l ⊃ r: {5} | {(2,), 3} | ø')
