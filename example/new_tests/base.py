from bdd_coder import decorators
from bdd_coder import tester

gherkin = decorators.Gherkin(logs_path='example/tests/bdd_runs.log')


@gherkin
class BddTester(tester.BddTester):
    """
    The decorated BddTester subclass of this tester package.
    It manages scenario runs. All test classes inherit from this one,
    so generic test methods for this package are expected to be defined here
    """
