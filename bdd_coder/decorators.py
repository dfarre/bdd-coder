"""To be employed with `BddTester` and `BaseTestCase`"""
import collections
import datetime
import itertools
import functools
import logging
from logging.handlers import RotatingFileHandler

import pytest

from bdd_coder import exceptions
from bdd_coder.features import StepSpec
from bdd_coder import stock
from bdd_coder.text_utils import OK, FAIL, PENDING, TO, COMPLETION_MSG, BOLD


class Step(StepSpec):
    def __init__(self, text, ordinal, scenario):
        super().__init__(text, ordinal, scenario.gherkin.aliases)
        self.scenario = scenario
        self.doc_scenario = None
        self.result = ''
        self.is_last = False
        self.method_qualname = ''

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

    @property
    def fixture_param(self):
        if self.inputs:
            return [self.inputs[0] if len(self.inputs) == 1 else self.inputs]

    @property
    def fixture_name(self):
        return f'{self.name}{id(self)}'

    def __str__(self):
        return (f'Doc scenario {self.name}' if self.doc_scenario is not None
                else super().__str__())

    def __call__(self, step_method):
        @functools.wraps(step_method)
        def logger_step_method(tester, *args, **kwargs):
            __tracebackhide__ = True

            try:
                self.result = step_method(tester, *args, **kwargs)
            except Exception:
                self.symbol = FAIL
                self.result = exceptions.format_next_traceback()
            else:
                self.symbol = OK

                if isinstance(self.result, tuple):
                    for name, value in zip(self.output_names, self.result):
                        self.gherkin.outputs[name].append(value)

            kwargs.pop('request', None)
            self.log(**kwargs)

            if self.is_last:
                self.scenario.log()

            if self.symbol == FAIL:
                pytest.fail(self.result)

        return pytest.fixture(name=self.fixture_name, params=self.fixture_param)(
            logger_step_method)

    def log(self, **kwargs):
        self.gherkin.logger.info(
            f'{datetime.datetime.utcnow()} '
            f'{self.symbol} {self.method_qualname}{self.format_parameters(**kwargs)}'
            f'{self.formatted_result}')

    def format_parameters(self, **kwargs):
        if not kwargs and not self.inputs:
            return ''

        text = '\n'.join(([f'    {", ".join(self.inputs)}'] if self.inputs else []) +
                         [f'    {n} = {repr(v)}' for n, v in kwargs.items()])

        return f'\n{text}'

    @property
    def formatted_result(self):
        if not self.result:
            return ''

        if isinstance(self.result, tuple) and self.result:
            text = '\n'.join([f'    {repr(v)}' for v in self.result])

            return f'\n  {TO} {text.lstrip()}'

        return f' {TO} {self.result}'

    @staticmethod
    def last_step(steps):
        for step in steps:
            if step.symbol in [FAIL, PENDING]:
                return step
        return step


class Scenario:
    def __init__(self, gherkin, *param_values):
        self.gherkin = gherkin
        self.param_values = param_values
        self.marked, self.ready = False, False

    @property
    def symbol(self):
        return Step.last_step(self.steps).symbol

    @property
    def param_names(self):
        names = []
        for name in itertools.chain(*(s.param_names for s in self.steps)):
            if name in names:
                raise exceptions.RedeclaredParametersError(params=name)
            else:
                names.append(name)
        return names

    def refine(self):
        fine_steps, param_ids, param_values = [], self.param_names, self.param_values
        wrong_values = [i for i, values in enumerate(param_values) if not (
            isinstance(values, list) and len(param_ids) == len(values))]

        if wrong_values:
            raise exceptions.WrongParametersError(
                name=self.name, positions=', '.join([str(i) for i in wrong_values]),
                length=len(param_ids))

        for step in self.steps:
            if step.doc_scenario is None:
                fine_steps.append(step)
            else:
                finesteps, paramids, paramvalues = step.doc_scenario.refine()
                reused_ids = set(param_ids) & set(paramids)

                if reused_ids:
                    raise exceptions.RedeclaredParametersError(params=', '.join(reused_ids))

                param_ids.extend(paramids)
                fine_steps.extend(finesteps)
                param_values = tuple(v1 + v2 for v1, v2 in zip(param_values, paramvalues))

        return fine_steps, param_ids, param_values

    def log(self):
        self.gherkin.logger.info(
            f'{datetime.datetime.utcnow()} {BOLD.get(self.symbol, self.symbol)} '
            f'{self.method.__qualname__}\n')

    def mark_method(self, method):
        self.steps = list(Step.generate_steps(method.__doc__.splitlines(), self))
        self.name = method.__name__
        self.steps[-1].is_last = True
        self.is_test = self.name.startswith('test_')
        self.gherkin[method.__qualname__] = self

        if self.is_test:
            return method

        @functools.wraps(method)
        def scenario_doc_method(tester, *args, **kwargs):
            raise AssertionError('Doc scenario method called')

        return scenario_doc_method

    def make_test_method(self, marked_method):
        fine_steps, param_ids, param_values = self.refine()

        @functools.wraps(marked_method)
        @pytest.mark.usefixtures(*(step.fixture_name for step in fine_steps))
        def scenario_test_method(tester, *args, **kwargs):
            __tracebackhide__ = True

            if self.symbol == PENDING:
                self.log()
                pytest.fail('Test did not complete!')

        if param_values:
            return pytest.mark.parametrize(
                ','.join(param_ids), param_values)(scenario_test_method)

        return scenario_test_method

    def __call__(self, method):
        if self.marked is False:
            self.method = self.mark_method(method)
            self.marked = True
        elif self.is_test and self.ready is False:
            self.method = self.make_test_method(method)
            self.ready = True

        return self.method


class Gherkin(stock.Repr):
    def __init__(self, aliases, validate=True, **logging_kwds):
        self.reset_logger(**logging_kwds)
        self.reset_outputs()
        self.passed, self.failed = 0, 0
        self.scenarios = collections.defaultdict(dict)
        self.aliases = aliases
        self.validate = validate
        self._parameter_ids = []

    def __call__(self, BddTester):
        self.BddTester = BddTester
        BddTester.gherkin = self

        return BddTester

    def __str__(self):
        passed = len(self.passed_scenarios)
        failed = len(self.failed_scenarios)
        pending = len(self.pending_scenarios)
        return ''.join([f'{passed}{BOLD[OK]}' if passed else '',
                        f'  {failed}{BOLD[FAIL]}' if failed else '',
                        f'  {pending}{PENDING}' if pending else f'  {COMPLETION_MSG}'])

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

    def scenario(self, *param_values):
        return Scenario(self, *param_values)
