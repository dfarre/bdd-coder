"""To be employed with `BddTester` and `BaseTestCase`"""

import collections
import datetime
import functools
import json
import os

from bdd_coder import get_step_specs
from bdd_coder import LOGS_DIR_NAME, FAIL

from bdd_coder import stock


class Steps(stock.Repr):
    def __init__(self, aliases, logs_parent, max_history_length=5, validate=True):
        self.logs_dir = os.path.join(logs_parent, LOGS_DIR_NAME)
        os.makedirs(self.logs_dir, exist_ok=True)
        self.max_history_length = max_history_length
        self.reset_outputs()
        self.run_number, self.passed, self.failed, self.scenarios = 0, 0, 0, {}
        self.exceptions = collections.defaultdict(list)
        self.aliases = aliases
        self.validate = validate

    def __call__(self, BddTester):
        BddTester.steps = self
        self.tester = BddTester  # TODO Many testers? One is supported

        return BddTester

    def __str__(self):
        runs = json.dumps(self.get_runs(), ensure_ascii=False, indent=4)
        pending = json.dumps(self.get_pending_runs(), ensure_ascii=False, indent=4)

        return f'Scenario runs {runs}\nPending {pending}'

    def get_runs(self):
        return collections.OrderedDict([
            ('-'.join(map(lambda r: f'{r[0]}{r[1]}', runs)), name)
            for name, runs in sorted(filter(lambda it: it[1], self.scenarios.items()),
                                     key=lambda it: it[1][0][0])])

    def get_pending_runs(self):
        return [method for method, runs in self.scenarios.items() if not runs]

    def clear_old_history(self):
        for log in sorted(os.listdir(self.logs_dir))[:-self.max_history_length]:
            os.remove(os.path.join(self.logs_dir, log))

    def write_to_history(self, text):
        log_path = os.path.join(self.logs_dir, f'{datetime.datetime.utcnow().date()}.log')

        with open(log_path, 'a' if os.path.isfile(log_path) else 'w') as history:
            history.write(text + '\n\n')

        self.clear_old_history()

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
            step_logs = list(test_case.run_steps(method.__doc__))
            symbol, message = step_logs[-1]
            test_case.log_scenario_run(method.__name__, step_logs, symbol)

            if symbol == FAIL:
                self.steps.failed += 1
                self.steps.exceptions[method.__name__].append(message)
                test_case.fail(message)
            else:
                self.steps.passed += 1

        return wrapper
