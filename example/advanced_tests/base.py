from bdd_coder import decorators
from bdd_coder import tester

gherkin = decorators.Gherkin(logs_path='example/advanced_tests/bdd_runs.log')


@gherkin
class BddTester(tester.BddTester):
    pass
