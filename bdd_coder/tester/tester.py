import datetime
import unittest

from bdd_coder import SUCCESS_MSG


class BddTester:
    """
    To be decorated with `Steps`, and employed with methods decorated with
    `scenario` - mix with a subclass of `BaseTestCase` to run test methods
    """

    @classmethod
    def log_scenario_run(cls, name, step_logs):
        cls.steps.run_number += 1
        cls.steps.scenarios[name].append(cls.steps.run_number)
        cls.steps.write_to_history(f'{cls.steps.run_number} ✓ {cls.__name__}.{name}:'
                                   + ''.join([f'\n  {cls.steps.run_number}.{n+1} - {text}'
                                              for n, text in enumerate(step_logs)]))

    def run_scenario(self, method_doc):
        def run_step(method_name, inputs, output_names):
            output = getattr(self, method_name)(*inputs) or ()

            for name, value in zip(output_names, output):
                self.steps.outputs[name].append(value)

            return (f'{datetime.datetime.utcnow()} ✓ '
                    f'{method_name} {inputs} |--> {output}')

        return [run_step(*args) for args in self.steps.get_step_specs(method_doc)]


class BaseTestCase(unittest.TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()

        end_note = '' if cls.steps.pending_runs else '\n\n' + SUCCESS_MSG
        cls.steps.write_to_history(f'{cls.__name__} - {cls.steps}{end_note}')

    def tearDown(self):
        self.steps.reset_outputs()
