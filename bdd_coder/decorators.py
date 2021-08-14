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
from bdd_coder.text_utils import (
    OK, FAIL, PENDING, TO, COMPLETION_MSG, BOLD, Style, indent, ExcInfo)


class StepRun(stock.Repr):
    def __init__(self, step, scenario_run):
        self.scenario_run = scenario_run
        self.step = step
        self.kwargs = {}
        self.result = None
        self.is_last = False

    @property
    def symbol(self):
        return getattr(self, '_StepRun__symbol', PENDING)

    @symbol.setter
    def symbol(self, value):
        self.__symbol = value
        self.__end_time = datetime.datetime.utcnow()
        self.log()

        if value == FAIL or value == OK and self.is_last:
            self.scenario_run.symbol = value

    @property
    def end_time(self):
        return getattr(self, '_StepRun__end_time', None)

    @end_time.setter
    def end_time(self, value):
        raise AttributeError("'end_time' is read-only")

    def __str__(self):
        return (f'{self.end_time} {self.symbol} {self.step.method_qualname}'
                f'{self.step.format_parameters(**self.kwargs)} {self.formatted_result}')

    @property
    def formatted_result(self):
        if isinstance(self.result, tuple) and self.result and self.symbol == OK:
            text = '\n'.join([f'    {repr(v)}' for v in self.result])

            return f'\n  {TO} {text.lstrip()}'

        if self.symbol == FAIL:
            return f'{TO} {self.result.highlighted_traceback}'

        return ''

    def log(self, **kwargs):
        lines = str(self).splitlines()
        lines[0] = f'├─{lines[0]}'
        lines[1:] = [f'|{line}' for line in lines[1:]]
        self.step.gherkin.logger.info('\n'.join(lines))


class ScenarioRun(stock.Repr):
    def __init__(self, test_id, scenario, parent_run=None):
        self.test_id = test_id
        self.scenario = scenario
        self.parent_run = parent_run
        self.is_last = False
        self.runs = [StepRun(step, self) if step.doc_scenario is None else ScenarioRun(
            test_id, step.doc_scenario, self) for step in scenario.steps]
        self.runs[-1].is_last = True

    def __iter__(self):
        yield self

        for run in self.runs:
            if isinstance(run, ScenarioRun):
                yield from run

    def __str__(self):
        qualname = self.scenario.qualname

        if self.symbol == FAIL:
            result_text = f' {TO} {self.result.exc_type.__name__}: {self.result.exc_value}'
        elif self.symbol == OK:
            result_text = f' {TO} {self.result}' if self.result else '.'

        return (f'{PENDING} {qualname}' if self.symbol == PENDING else
                f'{self.end_time} {BOLD[self.symbol]} {qualname}{result_text}')

    @property
    def result(self):
        for step_run in self.iter_step_runs():
            if step_run.symbol == FAIL:
                return step_run.result
        return step_run.result

    @property
    def symbol(self):
        return getattr(self, '_ScenarioRun__symbol', PENDING)

    @symbol.setter
    def symbol(self, value):
        self.__symbol = value
        self.__end_time = datetime.datetime.utcnow()
        self.log()

        if self.parent_run is not None and (value == FAIL or value == OK and self.is_last):
            self.parent_run.symbol = value

    @property
    def end_time(self):
        return getattr(self, '_ScenarioRun__end_time', None)

    @end_time.setter
    def end_time(self, value):
        raise AttributeError("'end_time' is read-only")

    def iter_step_runs(self):
        for run in self.runs:
            if isinstance(run, StepRun):
                yield run
            elif isinstance(run, ScenarioRun):
                yield from run.iter_step_runs()

    def get_pending_step_run(self, step):
        for step_run in self.iter_step_runs():
            if step_run.step == step and step_run.symbol == PENDING:
                return step_run

    def log(self):
        self.scenario.gherkin.logger.info('└─' + (
            f'{PENDING} {self.scenario.qualname}' if self.symbol == PENDING else
            f'{self.end_time} {BOLD[self.symbol]} {self.scenario.qualname}'))


class Step(StepSpec):
    def __init__(self, text, ordinal, scenario):
        super().__init__(text, ordinal, scenario.gherkin.aliases)
        self.scenario = scenario
        self.doc_scenario = None
        self.test_scenario = None
        self.method_qualname = ''

    @property
    def gherkin(self):
        return self.scenario.gherkin

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
            if tester.current_run.symbol != PENDING:
                return

            step_run = tester.current_run.get_pending_step_run(self)
            step_run.kwargs = {k: v for k, v in kwargs.items()
                               if k not in self.gherkin.fixtures_not_to_log}

            try:
                step_run.result = step_method(tester, *args, **kwargs)
            except Exception:
                step_run.result = ExcInfo()
                step_run.symbol = FAIL
            else:
                step_run.symbol = OK

                if isinstance(step_run.result, tuple):
                    for name, value in zip(self.output_names, step_run.result):
                        self.gherkin.outputs[name].append(value)

        return pytest.fixture(name=self.fixture_name, params=self.fixture_param)(
            logger_step_method)

    def format_parameters(self, **kwargs):
        if not kwargs and not self.inputs:
            return ''

        text = '\n'.join(([f'    {", ".join(self.inputs)}'] if self.inputs else []) +
                         [f'    {n} = {repr(v)}' for n, v in kwargs.items()])

        return f'\n{text}'


class Scenario(stock.Repr):
    def __init__(self, gherkin, *param_values):
        self.gherkin = gherkin
        self.param_values = param_values
        self.marked, self.ready = False, False

    def __str__(self):
        return f'{self.steps[0]}...{self.steps[-1]} params={self.param_names}'

    @property
    def name(self):
        return self.method.__name__

    @property
    def qualname(self):
        return self.method.__qualname__

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

                param_values = (tuple(v1 + v2 for v1, v2 in zip(param_values, paramvalues))
                                if param_values else paramvalues)

        return fine_steps, param_ids, param_values

    def mark_method(self, method):
        self.steps = list(Step.generate_steps(method.__doc__.splitlines(), self))
        self.gherkin[method.__qualname__] = self
        self.is_test = method.__name__.startswith('test_')

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

            if tester.current_run.symbol == FAIL:
                pytest.fail(msg=tester.current_run.result.next_traceback, pytrace=False)

        if len(param_ids) == 1:
            param_values = [v[0] for v in param_values]

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

        self.method.scenario = self

        return self.method


class Gherkin(stock.Repr):
    def __init__(self, aliases, validate=True, fixtures_not_to_log=('request',),
                 **logging_kwds):
        self.reset_logger(**logging_kwds)
        self.reset_outputs()
        self.scenarios = collections.defaultdict(dict)
        self.aliases = aliases
        self.validate = validate
        self.fixtures_not_to_log = fixtures_not_to_log
        self.test_runs = {}

    def __str__(self):
        return str(self.test_runs or self.scenarios)

    def __call__(self, BddTester):
        self.BddTester = BddTester
        BddTester.gherkin = self

        return BddTester

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

    def new_run(self, test_id, scenario):
        self.test_runs[test_id] = ScenarioRun(test_id, scenario)
        self.logger.info('_'*26)

    def reset_logger(self, logs_path, maxBytes=100000, backupCount=10):
        self.logger = logging.getLogger('bdd_test_runs')
        self.logger.setLevel(level=logging.INFO)
        handler = RotatingFileHandler(logs_path, maxBytes=maxBytes, backupCount=backupCount)
        handler.setFormatter(logging.Formatter('%(message)s'))
        self.logger.handlers.clear()
        self.logger.addHandler(handler)

    def log(self, fail_if_pending=False):
        __tracebackhide__ = True
        runs = self.get_scenario_runs()
        self.logger.info('\n' + ''.join([
            f'  {len(runs[OK])}{BOLD[OK]}' if runs[OK] else '',
            f'  {len(runs[FAIL])}{BOLD[FAIL]}' if runs[FAIL] else '',
            f'  {len(runs[PENDING])}{PENDING}' if runs[PENDING] else f'  {COMPLETION_MSG}'
        ]) + '\n')

        if runs[FAIL]:
            self.logger.info('  ' + Style.bold('Scenario failures summary:'))

            for name, sruns in runs[FAIL].items():
                for r in sruns:
                    self.logger.info(indent(str(r)) + '\n')

        if runs[PENDING] and fail_if_pending:
            names = ', '.join(list(runs[FAIL]))
            pytest.fail(f'These scenarios did not run: {names}')

    def get_scenario_runs(self, symbols=(OK, FAIL, PENDING)):
        return {symbol: collections.OrderedDict(itertools.groupby(
            filter(lambda s: s.symbol == symbol, itertools.chain(*self.test_runs.values())),
            key=lambda s: s.scenario.name)) for symbol in symbols}

    def reset_outputs(self):
        self.outputs = collections.defaultdict(list)

    def scenario(self, *param_values):
        return Scenario(self, *param_values)
