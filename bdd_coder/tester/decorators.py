"""To be employed with `BddTester` and `BaseTestCase`"""
import collections
import functools
import json
import logging
from logging.handlers import RotatingFileHandler

import pytest

from bdd_coder import FAIL
from bdd_coder import stock


class Steps(stock.Repr):
    def __init__(self, aliases, validate=True, **logging_kwds):
        self.reset_logger(**logging_kwds)
        self.reset_outputs()
        self.run_number, self.passed, self.failed, self.scenarios = 0, 0, 0, {}
        self.exceptions = collections.defaultdict(list)
        self.aliases = aliases
        self.validate = validate

    def __call__(self, BddTester):
        BddTester.steps = self
        self.tester = BddTester

        return BddTester

    def __str__(self):
        runs = json.dumps(self.get_runs(), ensure_ascii=False, indent=4)
        pending = json.dumps(self.get_pending_runs(), ensure_ascii=False, indent=4)

        return f'Scenario runs {runs}\nPending {pending}'

    def reset_logger(self, logs_path, maxBytes=100000, backupCount=10):
        self.logger = logging.getLogger('bdd_test_runs')
        self.logger.setLevel(level=logging.INFO)
        handler = RotatingFileHandler(logs_path, maxBytes=maxBytes, backupCount=backupCount)
        handler.setFormatter(logging.Formatter('%(message)s'))
        self.logger.handlers.clear()
        self.logger.addHandler(handler)

    def get_runs(self):
        return collections.OrderedDict([
            ('-'.join(map(lambda r: f'{r[0]}{r[1]}', runs)), name)
            for name, runs in sorted(filter(lambda it: it[1], self.scenarios.items()),
                                     key=lambda it: it[1][0][0])])

    def get_pending_runs(self):
        return [method for method, runs in self.scenarios.items() if not runs]

    def reset_outputs(self):
        self.outputs = collections.defaultdict(list)


try:
    import pytest_twisted
except ImportError:
    class Scenario:
        def __init__(self, steps):
            self.steps = steps

        def __call__(self, method):
            self.steps.scenarios[method.__name__] = []

            @functools.wraps(method)
            def wrapper(test_case, *args, **kwargs):
                step_logs = test_case.run_steps(method.__doc__)
                symbol, message = step_logs[-1]
                test_case.log_scenario_run(method.__name__, step_logs, symbol)

                if symbol == FAIL:
                    self.steps.failed += 1
                    self.steps.exceptions[method.__name__].append(message)
                    __tracebackhide__ = True
                    pytest.fail(message)
                else:
                    self.steps.passed += 1

            return wrapper
else:
    class Scenario:
        def __init__(self, steps):
            self.steps = steps

        def __call__(self, method):
            self.steps.scenarios[method.__name__] = []

            @functools.wraps(method)
            @pytest_twisted.inlineCallbacks
            def wrapper(test_case, *args, **kwargs):
                step_logs = yield test_case.run_steps(method.__doc__)
                symbol, message = step_logs[-1]
                test_case.log_scenario_run(method.__name__, step_logs, symbol)

                if symbol == FAIL:
                    self.steps.failed += 1
                    self.steps.exceptions[method.__name__].append(message)
                    __tracebackhide__ = True
                    pytest.fail(message)
                else:
                    self.steps.passed += 1

            return wrapper
