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
from bdd_coder.text_utils import OK, FAIL, PENDING, TO, COMPLETION_MSG, BOLD, Style, indent


class Run(stock.Repr):
    def __init__(self, test_id):
        self.test_id = test_id

    @property
    def symbol(self):
        return getattr(self, '_Run__symbol', PENDING)

    @symbol.setter
    def symbol(self, value):
        self.__symbol = value
        self.__end_time = datetime.datetime.utcnow()

    @property
    def end_time(self):
        return getattr(self, '_Run__end_time', None)

    @end_time.setter
    def end_time(self, value):
        raise AttributeError("'end_time' is read-only")


class StepRun(Run):
    def __init__(self, test_id, step, kwargs):
        super().__init__(test_id)
        self.step = step
        self.result = None
        self.kwargs = kwargs

    def __str__(self):
        return (f'{self.end_time} {self.symbol} {self.step.method_qualname}'
                f'{self.step.format_parameters(**self.kwargs)} {self.formatted_result}')

    @property
    def formatted_result(self):
        if not self.result:
            return ''

        if isinstance(self.result, tuple) and self.result:
            text = '\n'.join([f'    {repr(v)}' for v in self.result])

            return f'\n  {TO} {text.lstrip()}'

        return f' {TO} {self.result}'

    def log(self, **kwargs):
        self.step.gherkin.logger.info(str(self))


class IterableRun(Run):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.runs = []

    def __iter__(self):
        yield from self.runs

    def append_run(self, run):
        self.runs.append(run)

    @property
    def result(self):
        if self.symbol != PENDING:
            return self.runs[-1].result


class ScenarioRun(IterableRun):
    def __init__(self, test_id, scenario):
        super().__init__(test_id)
        self.scenario = scenario

    def __str__(self):
        return (f'{PENDING} ' if self.symbol == PENDING else
                f'{self.end_time} {BOLD[self.symbol]} ') + self.scenario.method.__qualname__

    def log(self):
        self.scenario.gherkin.logger.info(f'{self}\n')

    @property
    def runs_summary(self):
        qualname = self.scenario.method.__qualname__

        if not self.runs:
            return f'{PENDING} {qualname}'

        return '\n'.join([
            f'{run.end_time} {BOLD.get(run.symbol, run.symbol)} {qualname}'
            for run in self.runs])


class TestRun(IterableRun):
    def __init__(self, test_id, gherkin):
        super().__init__(test_id)
        self.gherkin = gherkin


class Step(StepSpec):
    def __init__(self, text, ordinal, scenario):
        super().__init__(text, ordinal, scenario.gherkin.aliases)
        self.scenario = scenario
        self.doc_scenario = None
        self.result = ''
        self.is_last = False
        self.is_first = False
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
            test_run = self.gherkin.setdefault_run(tester.pytest_request.node.name)

            if test_run.symbol != PENDING:
                return

            if self.is_first:
                scenario_run = ScenarioRun(tester.pytest_request.node.name, self.scenario)
                test_run.append_run(scenario_run)
            else:
                scenario_run = test_run.runs[-1]

            step_run = StepRun(tester.pytest_request.node.name, self, kwargs)
            scenario_run.append_run(step_run)

            try:
                step_run.result = step_method(tester, *args, **kwargs)
            except Exception:
                step_run.result = exceptions.format_next_traceback()
                step_run.symbol = FAIL
                scenario_run.symbol = FAIL
                test_run.symbol = FAIL
            else:
                step_run.symbol = OK

                if self.is_last:
                    scenario_run.symbol = OK

                if isinstance(step_run.result, tuple):
                    for name, value in zip(self.output_names, step_run.result):
                        self.gherkin.outputs[name].append(value)

            step_run.log()

            if scenario_run.symbol != PENDING:
                scenario_run.log()

        return pytest.fixture(name=self.fixture_name, params=self.fixture_param)(
            logger_step_method)

    def format_parameters(self, **kwargs):
        if not kwargs and not self.inputs:
            return ''

        text = '\n'.join(([f'    {", ".join(self.inputs)}'] if self.inputs else []) +
                         [f'    {n} = {repr(v)}' for n, v in kwargs.items()])

        return f'\n{text}'


class Scenario:
    def __init__(self, gherkin, *param_values):
        self.gherkin = gherkin
        self.param_values = param_values
        self.marked, self.ready = False, False

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

    def mark_method(self, method):
        self.steps = list(Step.generate_steps(method.__doc__.splitlines(), self))
        self.name = method.__name__
        self.steps[0].is_first = True
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
            test_run = self.gherkin.setdefault_run(tester.pytest_request.node.name)

            if test_run.symbol == FAIL:
                pytest.fail(msg=test_run.result, pytrace=False)

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

        return self.method


class Gherkin(stock.Repr):
    def __init__(self, aliases, validate=True, **logging_kwds):
        self.reset_logger(**logging_kwds)
        self.reset_outputs()
        self.scenarios = collections.defaultdict(dict)
        self.aliases = aliases
        self.validate = validate
        self.test_runs = {}

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

    def setdefault_run(self, test_id):
        return self.test_runs.setdefault(test_id, TestRun(test_id, self))

    def reset_logger(self, logs_path, maxBytes=100000, backupCount=10):
        self.logger = logging.getLogger('bdd_test_runs')
        self.logger.setLevel(level=logging.INFO)
        handler = RotatingFileHandler(logs_path, maxBytes=maxBytes, backupCount=backupCount)
        handler.setFormatter(logging.Formatter('%(message)s'))
        self.logger.handlers.clear()
        self.logger.addHandler(handler)

    def log(self):
        __tracebackhide__ = True
        passed = self.scenario_runs_ok
        failed = self.scenario_runs_failed
        pending = self.scenario_runs_pending
        self.logger.info('\n' + ''.join([
            f'  {len(passed)}{BOLD[OK]}' if passed else '',
            f'  {len(failed)}{BOLD[FAIL]}' if failed else '',
            f'  {len(pending)}{PENDING}' if pending else f'  {COMPLETION_MSG}']) + '\n')

        if failed:
            self.logger.info('  ' + Style.bold('Scenario failures summary:'))
            for scenario_run in failed:
                self.logger.info(indent(scenario_run.runs_summary))

        if pending:
            qualnames = ', '.join([r.scenario.method.__qualname__ for r in pending])
            pytest.fail(f'These scenarios did not run: {qualnames}')

    @property
    def scenario_runs(self):
        yield from itertools.chain(*self.test_runs.values())

    @property
    def scenario_runs_ok(self):
        return list(filter(lambda s: s.symbol == OK, self.scenario_runs))

    @property
    def scenario_runs_failed(self):
        return list(filter(lambda s: s.symbol == FAIL, self.scenario_runs))

    @property
    def scenario_runs_pending(self):
        return list(filter(lambda s: s.symbol == PENDING, self.scenario_runs))

    def reset_outputs(self):
        self.outputs = collections.defaultdict(list)

    def scenario(self, *param_values):
        return Scenario(self, *param_values)
