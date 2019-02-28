"""To be employed with `BddTestCase` and `BaseTestCase`"""

import collections
import datetime
import functools
import json
import os

from bdd_coder import get_step_specs
from bdd_coder import BaseRepr
from bdd_coder import LOGS_DIR_NAME


class Steps(BaseRepr):
    def __init__(self, aliases, logs_parent, max_history_length=5):
        self.logs_dir = os.path.join(logs_parent, LOGS_DIR_NAME)
        os.makedirs(self.logs_dir, exist_ok=True)
        self._clear_old_history(max_history_length)
        note = f'{datetime.datetime.utcnow()} Steps prepared'
        self.write_to_history('\n'.join(['_'*len(note), note]))
        self.reset_outputs()
        self.run_number, self.scenarios = 0, {}
        self.aliases = aliases

    def __call__(self, BddTestCase):
        BddTestCase.steps = self

        return BddTestCase

    def __str__(self):
        return (f'Scenario runs {json.dumps(self.get_runs(), indent=4)}\n'
                f'Pending {json.dumps(self.get_pending_runs(), indent=4)}')

    def get_runs(self):
        return collections.OrderedDict(map(
            lambda it: ('-'.join(map(str, it[1])), it[0]), sorted(filter(
                lambda it: it[1], self.scenarios.items()), key=lambda it: it[1][0])))

    def get_pending_runs(self):
        return [method for method, runs in self.scenarios.items() if not runs]

    def _clear_old_history(self, max_history_length):
        for log in sorted(os.listdir(self.logs_dir))[:-max_history_length]:
            os.remove(os.path.join(self.logs_dir, log))

    def write_to_history(self, text):
        log_path = os.path.join(
            self.logs_dir, f'{datetime.datetime.utcnow().date()}.log')

        with open(log_path, 'a' if os.path.isfile(log_path) else 'w') as history:
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
