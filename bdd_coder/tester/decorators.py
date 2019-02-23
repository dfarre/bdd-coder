"""To be employed with `BddTestCase` and `BaseTestCase`"""

import collections
import datetime
import functools
import json
import os

from bdd_coder import get_step_specs
from bdd_coder import BaseRepr


class Steps(BaseRepr):
    def __init__(self, aliases, tests_path, max_history_length=5):
        self.tests_path = tests_path
        self.history_dir = os.path.join(tests_path, 'bdd-run-logs')
        os.makedirs(self.history_dir, exist_ok=True)
        self._clear_old_history(max_history_length)
        note = f'{datetime.datetime.utcnow()} Steps prepared to run {self.tests_path}'
        self.write_to_history('\n'.join(['_'*len(note), note]))
        self.reset_outputs()
        self.run_number, self.scenarios = 0, {}
        self.aliases = aliases

    def __call__(self, BddTestCase):
        BddTestCase.steps = self

        return BddTestCase

    def __str__(self):
        runs = dict(map(lambda it: ('-'.join(map(str, it[1])), it[0]), self.runs.items()))

        return (f'Scenario runs {json.dumps(runs, indent=4)}\n'
                f'Pending {json.dumps(self.pending_runs, indent=4)}')

    @property
    def runs(self):
        return collections.OrderedDict(sorted(filter(
            lambda it: it[1], self.scenarios.items()), key=lambda it: it[1][0]))

    @property
    def pending_runs(self):
        return [name for name, runs in self.scenarios.items() if not runs]

    def _clear_old_history(self, max_history_length):
        for log in sorted(os.listdir(self.history_dir))[:-max_history_length]:
            os.remove(os.path.join(self.history_dir, log))

    def write_to_history(self, text):
        history_path = os.path.join(
            self.history_dir, f'{datetime.datetime.utcnow().date()}.log')

        with open(history_path, 'a' if os.path.isfile(history_path) else 'w') as history:
            history.write(text + '\n\n')

    def get_step_specs(self, method_doc):
        return get_step_specs(method_doc.splitlines(), self.aliases)

    def reset_outputs(self):
        self.outputs = collections.defaultdict(list)


class Scenario:
    def __init__(self, steps):
        self.steps = steps

    def __call__(self, method):
        self.steps.scenarios[method.__name__] = []

        @functools.wraps(method)
        def wrapper(test_case, *args, **kwargs):
            step_logs = test_case.run_scenario(method.__doc__)
            test_case.log_scenario_run(method.__name__, step_logs)

        return wrapper
