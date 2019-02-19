import collections
import functools

from bdd_coder import get_step_specs


class Steps:
    def __init__(self, steps_mapping):
        self.steps = steps_mapping

    def __call__(self, BaseTestCase):
        BaseTestCase.get_step_specs = self.get_step_specs

        return BaseTestCase

    def get_step_specs(self, method_doc):
        return get_step_specs(method_doc.splitlines(), self.steps)


def scenario(method):
    outputs = collections.defaultdict(list)

    @functools.wraps(method)
    def wrapper(self):
        for method_name, inputs, output_names in self.get_step_specs(method.__doc__):
            output = getattr(self, method_name)(*inputs, **outputs) or ()

            for name, value in zip(output_names, output):
                outputs[name].append(value)

    return wrapper
