import collections
import functools

from bdd_coder import get_step_specs


class Steps:
    def __init__(self, steps_mapping, tests_path):
        self.steps_mapping = steps_mapping
        self.tests_path = tests_path
        self.text = ''
        self.outputs = collections.defaultdict(list)

    def __call__(self, BaseTestCase):
        BaseTestCase.get_step_specs = self.get_step_specs
        BaseTestCase.steps = self

        return BaseTestCase

    def get_step_specs(self, method_doc):
        return get_step_specs(method_doc.splitlines(), self.steps_mapping)


def scenario(method):
    @functools.wraps(method)
    def wrapper(test_case):
        test_case.run_scenario(method.__name__, method.__doc__)

    return wrapper
