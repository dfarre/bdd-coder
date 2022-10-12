from bdd_coder import decorators
from bdd_coder import tester


class BddTester(tester.BddTester):
    gherkin = decorators.Gherkin(logs_path='example/tests/bdd_runs.log')
