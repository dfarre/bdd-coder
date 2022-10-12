from bdd_coder import decorators
from bdd_coder import tester


class BddTester(tester.BddTester):
    gherkin = decorators.Gherkin(logs_path='example/advanced_tests/bdd_runs.log', propagate_logs=True)
