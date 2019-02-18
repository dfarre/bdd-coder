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
    @functools.wraps(method)
    def wrapper(self, *args, **kwargs):
        for method_name, inputs, output_names in self.get_step_specs(method.__doc__):
            output = getattr(self, method_name)(*inputs, **kwargs)

            if output_names:
                kwargs.update(dict(zip(output_names, output)))

    return wrapper
