"""To be employed with `BddTester` and `BaseTestCase`"""
import collections
import datetime
import functools
from itertools import chain
import logging
from logging.handlers import RotatingFileHandler

import pytest

from bdd_coder import exceptions
from bdd_coder.features import StepSpec
from bdd_coder import stock
from bdd_coder import OK, FAIL, PENDING, TO, COMPLETION_MSG


class Step(StepSpec):
    def __init__(self, text, ordinal, scenario):
        super().__init__(text, ordinal, scenario.gherkin.aliases)
        self.scenario = scenario
        self.result = ''
        self.ready = False
        self.doc_scenario = None

    @property
    def gherkin(self):
        return self.scenario.gherkin

    @property
    def symbol(self):
        return (getattr(self, '_Step__symbol', PENDING) if self.doc_scenario is None
                else self.doc_scenario.symbol)

    @symbol.setter
    def symbol(self, value):
        assert self.doc_scenario is None, 'Cannot set doc scenario symbol'
        self.__symbol = value

    def __str__(self):
        return (f'Doc doc_scenario {self.name}' if self.doc_scenario is not None
                else super().__str__())

    def __call__(self, step_method):
        @functools.wraps(step_method)
        def logger_step_method(tester, *args, **kwargs):
            try:
                self.result = step_method(tester, *self.inputs, *args, **kwargs)
            except Exception:
                self.symbol = FAIL
                self.result = exceptions.format_next_traceback()
            else:
                self.symbol = OK

                if isinstance(self.result, tuple):
                    for name, value in zip(self.output_names, self.result):
                        self.gherkin.outputs[name].append(value)

            self.gherkin.logger.info(
                f'{datetime.datetime.utcnow()} {self.gherkin.test_number}.{self.ordinal} '
                f'{self.symbol} {step_method.__qualname__} {self.inputs} '
                f'{TO} {self.result or ()}')

        logger_step_method.ready = True

        return pytest.fixture(name=self.name)(logger_step_method)

    @staticmethod
    def refine_steps(steps):
        for i, step in enumerate(chain(*(
                [s] if s.doc_scenario is None else s.doc_scenario.steps for s in steps))):
            step.ordinal = i
            yield step

    @staticmethod
    def last_step(steps):
        for step in steps:
            if step.symbol in [FAIL, PENDING]:
                return step
        return step


class Scenario:
    def __init__(self, gherkin, parameters=()):
        self.gherkin = gherkin
        self.parameters = parameters
        self.marked, self.ready = False, False

    @property
    def symbol(self):
        return Step.last_step(self.steps).symbol

    def __call__(self, method):
        if self.marked is False:
            self.name = method.__name__
            self.steps = list(Step.generate_steps(method.__doc__.splitlines(), self))
            self.is_test = self.name.startswith('test_')
            self.marked = True
            self.gherkin[method.__qualname__] = self

            if self.is_test:
                return method

            @functools.wraps(method)
            def scenario_doc_method(tester, *args, **kwargs):
                raise AssertionError('Doc scenario method called')

            return scenario_doc_method

        if self.is_test and self.ready is False:
            steps = list(Step.refine_steps(self.steps))

            @functools.wraps(method)
            @pytest.mark.usefixtures(*(step.name for step in steps))
            def scenario_test_method(tester, *args, **kwargs):
                __tracebackhide__ = True
                self.gherkin.test_number += 1
                last_step = Step.last_step(steps)

                if last_step.symbol == FAIL:
                    pytest.fail(last_step.result)
                elif last_step.symbol == PENDING:
                    pytest.fail('Test did not complete!')

            self.ready = True

            return scenario_test_method

        return method


class Gherkin(stock.Repr):
    def __init__(self, aliases, validate=True, **logging_kwds):
        self.reset_logger(**logging_kwds)
        self.reset_outputs()
        self.test_number, self.passed, self.failed = 0, 0, 0
        self.scenarios = collections.defaultdict(dict)
        self.aliases = aliases
        self.validate = validate

    def __call__(self, BddTester):
        self.BddTester = BddTester
        BddTester.gherkin = self

        return BddTester

    def __str__(self):
        passed = len(self.passed_scenarios)
        failed = len(self.failed_scenarios)
        pending = len(self.pending_scenarios)
        return ''.join([f'{passed}{OK}' if passed else '',
                        f'  {failed}{FAIL}' if failed else '',
                        f'  {pending}{PENDING}' if pending else f'   {COMPLETION_MSG}'])

    def __contains__(self, scenario_qualname):
        class_name, method_name = scenario_qualname.split('.')

        return class_name in self.scenarios and method_name in self.scenarios[class_name]

    def __getitem__(self, scenario_qualname):
        class_name, method_name = scenario_qualname.split('.')

        return self.scenarios[class_name][method_name]

    def __setitem__(self, scenario_qualname, scenario_method):
        class_name, method_name = scenario_qualname.split('.')
        self.scenarios[class_name][method_name] = scenario_method

    def __iter__(self):
        for class_name in self.scenarios:
            yield from self.scenarios[class_name].values()

    def reset_logger(self, logs_path, maxBytes=100000, backupCount=10):
        self.logger = logging.getLogger('bdd_test_runs')
        self.logger.setLevel(level=logging.INFO)
        handler = RotatingFileHandler(logs_path, maxBytes=maxBytes, backupCount=backupCount)
        handler.setFormatter(logging.Formatter('%(message)s'))
        self.logger.handlers.clear()
        self.logger.addHandler(handler)

    @property
    def passed_scenarios(self):
        return list(filter(lambda s: s.symbol == OK, self))

    @property
    def failed_scenarios(self):
        return list(filter(lambda s: s.symbol == FAIL, self))

    @property
    def pending_scenarios(self):
        return list(filter(lambda s: s.symbol == PENDING, self))

    def reset_outputs(self):
        self.outputs = collections.defaultdict(list)

    def scenario(self, parameters=()):
        return Scenario(self, parameters)
