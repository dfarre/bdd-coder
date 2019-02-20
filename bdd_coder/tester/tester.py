import os
import unittest


class BddTestCase(unittest.TestCase):
    def run_scenario(self, name, method_doc):
        def run_step(method_name, inputs, output_names):
            output = getattr(self, method_name)(*inputs) or ()

            for name, value in zip(output_names, output):
                self.steps.outputs[name].append(value)

            return f'{method_name} {inputs} |--> {output_names}'

        history_path = os.path.join(os.path.dirname(self.steps.tests_path), 'history.log')

        with open(history_path, 'a') as history:
            history.write(f'\n\n* {name}\n  - ' + '\n  - '.join([
                run_step(*args) for args in self.get_step_specs(method_doc)]))
