"""To be employed with `BddTester` and `BaseTestCase`"""
import collections
import datetime
import functools
from itertools import chain
import json
import logging
from logging.handlers import RotatingFileHandler
import re

import pytest

from bdd_coder import exceptions
from bdd_coder import stock
from bdd_coder import I_REGEX, O_REGEX, OK, FAIL, TO
from bdd_coder import strip_lines, sentence_to_name, sentence_to_method_name


class Step(stock.Repr):
    def __init__(self, text, ordinal, aliases=None, gherkin=None):
        self.gherkin = gherkin
        self.text = text.strip().split(maxsplit=1)[1].strip()
        self.validate()
        self.aliases = aliases or {}
        self.own = False
        self.result, self.symbol = '', ''
        self.ready = False
        self.scenario = None
        self.ordinal = ordinal

    def __str__(self):
        own = 'i' if self.own else 'o'

        if self.scenario is not None:
            return f'Scenario ({own}) {self.name}'

        output_names = ', '.join(self.output_names)

        return f'({own}) {self.name} {self.inputs} {TO} ({output_names})'

    def __call__(self, step_method):
        if step_method.__qualname__ in self.gherkin:
            self.scenario = self.gherkin[step_method.__qualname__]
            self.ready = True
            return step_method

        @functools.wraps(step_method)
        def logger_step_method(tester, *args, **kwargs):
            try:
                self.result = step_method(tester, *self.inputs, *args, **kwargs)
                self.symbol = OK

                if isinstance(self.result, tuple):
                    for name, value in zip(self.output_names, self.result):
                        self.gherkin.outputs[name].append(value)
            except Exception:
                self.symbol = FAIL
                self.result = exceptions.format_next_traceback()

            self.gherkin.logger.info(
                f'{datetime.datetime.utcnow()} {self.gherkin.run_number}.{self.ordinal} '
                f'{self.symbol} {step_method.__qualname__} {self.inputs} '
                f'{TO} {self.result or ()}')

        self.ready = True

        return pytest.fixture(name=self.name)(logger_step_method)

    @classmethod
    def generate_steps(cls, lines, *args, **kwargs):
        return (cls(line, i, *args, **kwargs) for i, line in enumerate(strip_lines(lines)))

    @staticmethod
    def refine_steps(steps):
        for i, step in enumerate(chain(*(
                [s] if s.scenario is None else s.scenario.steps for s in steps))):
            step.ordinal = i
            yield step

    @staticmethod
    def last_step(steps):
        for step in steps:
            if step.symbol == FAIL:
                return step
        return step

    def validate(self):
        inputs_ok = self.inputs == self.get_inputs_by(r'"([^"]+)"')
        outputs_ok = self.output_names == self.get_output_names_by(r'`([^`]+)`')

        if not (inputs_ok and outputs_ok):
            raise exceptions.FeaturesSpecError(
                f'Inputs (by ") or outputs (by `) from {self.text} not understood')

    def get_inputs_by(self, regex):
        return re.findall(regex, self.text)

    def get_output_names_by(self, regex):
        return tuple(sentence_to_name(s) for s in re.findall(regex, self.text))

    @property
    def name(self):
        method = sentence_to_method_name(self.text)

        return self.aliases.get(method, method)

    @property
    def inputs(self):
        return self.get_inputs_by(I_REGEX)

    @property
    def output_names(self):
        return self.get_output_names_by(O_REGEX)


class Gherkin(stock.Repr, stock.TieDecorator):
    def __init__(self, aliases, validate=True, **logging_kwds):
        self.reset_logger(**logging_kwds)
        self.reset_outputs()
        self.run_number, self.passed, self.failed = 0, 0, 0
        self.scenarios = collections.defaultdict(dict)
        self.exceptions = collections.defaultdict(list)
        self.aliases = aliases
        self.validate = validate

    def __str__(self):
        runs = json.dumps(self.get_runs(), ensure_ascii=False, indent=4)
        pending = json.dumps(self.get_pending_runs(), ensure_ascii=False, indent=4)

        return f'Scenario runs {runs}\nPending {pending}'

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

    def get_runs(self):
        return collections.OrderedDict([
            ('-'.join(map(lambda r: f'{r[0]}{r[1]}', method.runs)), method.__qualname__)
            for method in sorted(filter(lambda m: m.runs, self), key=lambda m: m.runs[0][0])])

    def get_pending_runs(self):
        return [method.__qualname__ for method in self if not method.runs]

    def reset_outputs(self):
        self.outputs = collections.defaultdict(list)

    def scenario(self, method):
        method.steps = list(Step.generate_steps(
            method.__doc__.splitlines(), self.aliases, self))
        method.runs = []
        self[method.__qualname__] = method

        return method
