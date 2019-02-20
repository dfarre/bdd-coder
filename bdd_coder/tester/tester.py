import collections
import unittest


class BddTestCase(unittest.TestCase):
    @classmethod
    def tearDownClass(cls):
        print(cls.steps.text)
        super().tearDownClass()

    def run_scenario(self, name, method_doc):
        outputs = collections.defaultdict(list)

        def run_step(method_name, inputs, output_names):
            output = getattr(self, method_name)(*inputs, **outputs) or ()

            for name, value in zip(output_names, output):
                outputs[name].append(value)

            return f'{method_name} {inputs} |--> {output_names}'

        self.steps.text += f'\n\n* {name}\n  - ' + '\n  - '.join([
            run_step(*args) for args in self.get_step_specs(method_doc)])
