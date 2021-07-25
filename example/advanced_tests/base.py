from bdd_coder import decorators
from bdd_coder import tester

from . import aliases

gherkin = decorators.Gherkin(aliases.MAP, logs_path='example/advanced_tests/bdd_runs.log')


@gherkin
class BddTester(tester.BddTester):
    def board_x_is_added_to_the_game(self, *args):
        pass
