from bdd_coder import decorators
from bdd_coder import tester

from . import aliases

gherkin = decorators.Gherkin(aliases.MAP, logs_path='example/new_advanced_tests/bdd_runs.log')


@gherkin
class BddTester(tester.BddTester):
    pass
