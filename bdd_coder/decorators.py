"""To be employed with `BddTester`"""
from __future__ import annotations

import inspect

from collections import OrderedDict, defaultdict

import datetime
import itertools
import functools
import logging
from logging.handlers import RotatingFileHandler

from typing import Callable, Iterator, Optional, Union

import pytest
import pytest_asyncio

from bdd_coder import exceptions
from bdd_coder.features import StepSpec
from bdd_coder import stock
from bdd_coder.text_utils import (
    OK, FAIL, PENDING, TO, COMPLETION_MSG, BOLD, Style, indent, ExcInfo)


class StepRun(stock.Repr):
    def __init__(self, step: StepSpec, scenario_run: ScenarioRun):
        self.scenario_run = scenario_run
        self.step = step
        self.kwargs: dict = {}
        self.result: Optional[Union[tuple, ExcInfo]] = None
        self.is_last: bool = False

    @property
    def symbol(self) -> str:
        return getattr(self, '_StepRun__symbol', PENDING)

    @symbol.setter
    def symbol(self, value):
        self.__symbol = value
        self.__end_time = datetime.datetime.utcnow()
        self.log()

        if value == FAIL or value == OK and self.is_last:
            self.scenario_run.symbol = value

    @property
    def end_time(self) -> Optional[datetime.datetime]:
        return getattr(self, '_StepRun__end_time', None)

    @end_time.setter
    def end_time(self, value):
        raise AssertionError("'end_time' is read-only")

    def __str__(self) -> str:
        return (f'{self.end_time} {self.symbol} {self.step.method_qualname}'
                f'{self.step.format_parameters(**self.kwargs)} {self.formatted_result}')

    @property
    def formatted_result(self) -> str:
        if isinstance(self.result, tuple) and self.result and self.symbol == OK:
            text = '\n'.join([f'    {repr(v)}' for v in self.result])

            return f'\n  {TO} {text.lstrip()}'

        if self.symbol == FAIL and isinstance(self.result, ExcInfo):
            return f'{TO} {self.result.highlighted_traceback}'

        return ''

    def log(self):
        lines = str(self).splitlines()
        lines[0] = f'├─{lines[0]}'
        lines[1:] = [f'|{line}' for line in lines[1:]]
        self.step.gherkin.log_message('\n'.join(lines))


class ScenarioRun(stock.Repr):
    def __init__(self, test_id: int, scenario: Scenario, parent_run: Optional[ScenarioRun] = None):
        self.test_id = test_id
        self.scenario = scenario
        self.parent_run = parent_run
        self.is_last: bool = False
        self.runs: list[Union[StepRun, ScenarioRun]] = [
            StepRun(step, self) if step.doc_scenario is None else ScenarioRun(
                test_id, step.doc_scenario, self) for step in scenario.steps]
        self.runs[-1].is_last = True

    def __iter__(self) -> Iterator[ScenarioRun]:
        yield self

        for run in self.runs:
            if isinstance(run, ScenarioRun):
                yield from run

    def __str__(self) -> str:
        qualname = self.scenario.qualname

        if self.symbol == FAIL and isinstance(self.result, ExcInfo):
            result_text = f' {TO} {self.result.exc_type.__name__}: {self.result.exc_value}'
        elif self.symbol == OK:
            result_text = f' {TO} {self.result}' if self.result else '.'

        return (f'{PENDING} {qualname}' if self.symbol == PENDING else
                f'{self.end_time} {BOLD[self.symbol]} {qualname}{result_text}')

    @property
    def result(self) -> Union[tuple, ExcInfo]:
        for step_run in self.iter_step_runs():
            if step_run.symbol == FAIL:
                return step_run.result
        return step_run.result

    @property
    def symbol(self) -> str:
        return getattr(self, '_ScenarioRun__symbol', PENDING)

    @symbol.setter
    def symbol(self, value):
        self.__symbol = value
        self.__end_time = datetime.datetime.utcnow()
        self.log()

        if self.parent_run is not None and (value == FAIL or value == OK and self.is_last):
            self.parent_run.symbol = value

    @property
    def end_time(self) -> Optional[datetime.datetime]:
        return getattr(self, '_ScenarioRun__end_time', None)

    @end_time.setter
    def end_time(self, value):
        raise AssertionError("'end_time' is read-only")

    def iter_step_runs(self) -> Iterator[StepRun]:
        for run in self.runs:
            if isinstance(run, StepRun):
                yield run
            elif isinstance(run, ScenarioRun):
                yield from run.iter_step_runs()

    def get_pending_step_run(self, step) -> Optional[StepRun]:
        for step_run in self.iter_step_runs():
            if step_run.step == step and step_run.symbol == PENDING:
                return step_run
        return None

    def log(self):
        self.scenario.gherkin.log_message('└─' + (
            f'{PENDING} {self.scenario.qualname}' if self.symbol == PENDING else
            f'{self.end_time} {BOLD[self.symbol]} {self.scenario.qualname}'))


class Step(StepSpec):
    def __init__(self, text: str, ordinal: int, scenario: Scenario):
        super().__init__(text, ordinal)
        self.scenario = scenario
        self.doc_scenario: Optional[Scenario] = None
        self.test_scenario: Optional[Scenario] = None
        self.is_coroutine: bool

    @property
    def gherkin(self) -> Gherkin:
        return self.scenario.gherkin

    @property
    def fixture_param(self) -> Optional[list]:
        if self.inputs:
            return [self.inputs[0] if len(self.inputs) == 1 else self.inputs]
        return None

    @property
    def fixture_name(self) -> str:
        return f'{self.name}{id(self)}'

    def __str__(self) -> str:
        return (f'Doc scenario {self.name}' if self.doc_scenario is not None
                else super().__str__())

    def __call__(self, step_method: Callable) -> Callable:
        self.is_coroutine = inspect.iscoroutinefunction(step_method)

        return (self.make_async_step_method if self.is_coroutine else
                self.make_sync_step_method)(step_method)

    def make_sync_step_method(self, sync_method: Callable) -> Callable:
        @pytest.fixture(name=self.fixture_name, params=self.fixture_param)
        @functools.wraps(sync_method)
        def logger_step_method(tester, *args, **kwargs):
            if tester.current_run.symbol != PENDING:
                return

            step_run = tester.current_run.get_pending_step_run(self)
            step_run.kwargs = {k: v for k, v in kwargs.items()
                               if k not in self.gherkin.fixtures_not_to_log}
            tester.param = self.fixture_param[0] if self.inputs else ()

            try:
                step_run.result = sync_method(tester, *args, **kwargs)
            except Exception:
                step_run.result = ExcInfo()
                step_run.symbol = FAIL
            else:
                step_run.symbol = OK

                if isinstance(step_run.result, tuple):
                    for name, value in zip(self.output_names, step_run.result):
                        self.gherkin.outputs[name].append(value)
        return logger_step_method

    def make_async_step_method(self, coroutine_method: Callable) -> Callable:
        @pytest_asyncio.fixture(name=self.fixture_name, params=self.fixture_param)
        @functools.wraps(coroutine_method)
        async def logger_step_method(tester, *args, **kwargs):
            if tester.current_run.symbol != PENDING:
                return

            step_run = tester.current_run.get_pending_step_run(self)
            step_run.kwargs = {k: v for k, v in kwargs.items()
                               if k not in self.gherkin.fixtures_not_to_log}
            tester.param = self.fixture_param[0] if self.inputs else ()

            try:
                step_run.result = await coroutine_method(tester, *args, **kwargs)
            except Exception:
                step_run.result = ExcInfo()
                step_run.symbol = FAIL
            else:
                step_run.symbol = OK

                if isinstance(step_run.result, tuple):
                    for name, value in zip(self.output_names, step_run.result):
                        self.gherkin.outputs[name].append(value)
        return logger_step_method


class Scenario(stock.Repr):
    def __init__(self, gherkin: Gherkin, *param_values):
        self.gherkin = gherkin
        self.param_values = param_values
        self.marked: bool = False
        self.ready: bool = False
        self.steps: list[Step]
        self.is_test: bool
        self.is_coroutine: bool

    def __str__(self) -> str:
        return f'{self.steps[0]}...{self.steps[-1]} params={self.param_names}'

    @property
    def name(self) -> str:
        return self.method.__name__

    @property
    def qualname(self) -> str:
        return self.method.__qualname__

    @property
    def param_names(self) -> list[str]:
        names = []
        for name in itertools.chain(*(s.param_names for s in self.steps)):
            if name in names:
                raise exceptions.RedeclaredParametersError(params=name)
            else:
                names.append(name)
        return names

    def refine(self) -> tuple[list[Step], list[str], tuple]:
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

    def make_test_method(self, marked_method: Callable) -> Callable:
        fine_steps, param_ids, param_values = self.refine()
        self.is_coroutine = any(step.is_coroutine for step in fine_steps)

        scenario_test_method = (self.make_async_test_method if self.is_coroutine else
                                self.make_sync_test_method)(marked_method, fine_steps)

        if len(param_ids) == 1:
            param_values = tuple(v[0] for v in param_values)

        if param_values:
            return pytest.mark.parametrize(','.join(param_ids), param_values)(scenario_test_method)

        return scenario_test_method

    def make_sync_test_method(self, marked_method: Callable, fine_steps: list) -> Callable:
        @functools.wraps(marked_method)
        @pytest.mark.usefixtures(*(step.fixture_name for step in fine_steps))
        def scenario_test_method(tester, *args, **kwargs):
            __tracebackhide__ = True

            if tester.current_run.symbol == FAIL:
                pytest.fail(reason=tester.current_run.result.next_traceback, pytrace=False)

        return scenario_test_method

    def make_async_test_method(self, marked_method: Callable, fine_steps: list) -> Callable:
        @functools.wraps(marked_method)
        @pytest.mark.usefixtures(*(step.fixture_name for step in fine_steps))
        @pytest.mark.asyncio
        async def scenario_test_method(tester, *args, **kwargs):
            __tracebackhide__ = True

            if tester.current_run.symbol == FAIL:
                pytest.fail(reason=tester.current_run.result.next_traceback, pytrace=False)

        return scenario_test_method

    def __call__(self, method) -> Callable:
        if self.marked is False:
            self.method = self.mark_method(method)
            self.marked = True
        elif self.is_test and self.ready is False:
            self.method = self.make_test_method(method)
            self.ready = True

        self.method.scenario = self

        return self.method


class Gherkin(stock.Repr):
    BDD_RUN_LOG_LEVEL = 5

    def __init__(self, validate: bool = True, fixtures_not_to_log: tuple[str, ...] = ('request',),
                 **logging_kwds):
        self.reset_logger(**logging_kwds)
        self.reset_outputs()
        self.scenarios: dict[str, dict[str, Callable]] = defaultdict(dict)
        self.validate = validate
        self.fixtures_not_to_log = fixtures_not_to_log
        self.test_runs: dict = {}

    def __str__(self) -> str:
        return str(self.test_runs or self.scenarios)

    def __call__(self, *param_values) -> Scenario:
        return Scenario(self, *param_values)

    def __iter__(self) -> Iterator[Callable]:
        for class_name in self.scenarios:
            yield from self.scenarios[class_name].values()

    def __contains__(self, scenario_qualname: str):
        class_name, method_name = scenario_qualname.split('.')

        return class_name in self.scenarios and method_name in self.scenarios[class_name]

    def __getitem__(self, scenario_qualname: str):
        class_name, method_name = scenario_qualname.split('.')

        return self.scenarios[class_name][method_name]

    def __setitem__(self, scenario_qualname: str, scenario_method: Callable):
        class_name, method_name = scenario_qualname.split('.')
        self.scenarios[class_name][method_name] = scenario_method

    def new_run(self, test_id: int, scenario: Scenario):
        self.test_runs[test_id] = ScenarioRun(test_id, scenario)
        self.log_message('_'*26)

    def reset_logger(self, propagate_logs: bool = False, logs_path: str = './',
                     maxBytes: int = 1000000, backupCount: int = 10):
        self.logger = logging.getLogger('bdd_test_runs')
        logging.addLevelName(self.BDD_RUN_LOG_LEVEL, 'BDDR')
        self.logger.setLevel(level=self.BDD_RUN_LOG_LEVEL)
        handler = RotatingFileHandler(logs_path, maxBytes=maxBytes, backupCount=backupCount)
        handler.setFormatter(logging.Formatter('%(message)s'))
        self.logger.handlers.clear()
        self.logger.addHandler(handler)
        self.logger.propagate = propagate_logs

    def log_message(self, *args):
        self.logger.log(self.BDD_RUN_LOG_LEVEL, *args)

    def log(self, fail_if_pending: bool = False):
        __tracebackhide__ = True
        runs = self.get_scenario_runs()
        self.log_message('\n' + ''.join([
            f'  {len(runs[OK])}{BOLD[OK]}' if runs[OK] else '',
            f'  {len(runs[FAIL])}{BOLD[FAIL]}' if runs[FAIL] else '',
            f'  {len(runs[PENDING])}{PENDING}' if runs[PENDING] else f'  {COMPLETION_MSG}'
        ]) + '\n')
        failed_runs = list(itertools.chain(*runs[FAIL].values()))

        if failed_runs:
            self.log_message('  ' + Style.bold('Scenario failures summary:'))

            for run in failed_runs:
                self.log_message(indent(str(run)) + '\n')

        if runs[PENDING] and fail_if_pending:
            names = ', '.join(list(runs[PENDING]))
            pytest.fail(reason=f'These scenarios did not run: {names}')

    def get_scenario_runs(self, symbols=(OK, FAIL, PENDING)) -> dict[str, OrderedDict]:
        return {symbol: OrderedDict(itertools.groupby(
            filter(lambda s: s.symbol == symbol, itertools.chain(*self.test_runs.values())),
            key=lambda s: s.scenario.name)) for symbol in symbols}

    def reset_outputs(self):
        self.outputs = defaultdict(list)
