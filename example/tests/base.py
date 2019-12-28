from bdd_coder.tester import decorators
from bdd_coder.tester import tester

from . import aliases

steps = decorators.Steps(aliases.MAP, 'example/tests')
scenario = decorators.Scenario(steps)


@steps
class BddTester(tester.BddTester):
    pass


class BaseTestCase(tester.BaseTestCase):
    def board__is_added_to_the_game(self, *args):
        pass
