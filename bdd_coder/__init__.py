"""Common utils and constants"""

import re

from . import exceptions
from . import stock

BASE_TEST_CASE_NAME = 'BaseTestCase'
BASE_TESTER_NAME = 'BddTester'

COMPLETION_MSG = 'All scenarios ran'
OK, FAIL, TO = '✅', '❌', '↦'

IO_REGEX = r'[^"`]+'
I_REGEX, O_REGEX = rf'"({IO_REGEX})"', rf'`({IO_REGEX})`'


class Step(stock.Repr):
    def __init__(self, text, aliases=None):
        self.text = text.strip().split(maxsplit=1)[1].strip()
        self.validate()
        self.aliases = aliases or {}
        self.own = False

    def __str__(self):
        own = 'i' if self.own else 'o'
        output_names = ', '.join(self.output_names)

        return f'({own}) {self.name} {self.inputs} {TO} ({output_names})'

    @classmethod
    def steps(cls, lines, *args, **kwargs):
        return (cls(line, *args, **kwargs) for line in strip_lines(lines))

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


def to_sentence(name):
    return name.replace('__', ' "x" ').replace('_', ' ').capitalize()


def sentence_to_method_name(text):
    return re.sub(r'_{3,}', '__', sentence_to_name(re.sub(I_REGEX, '_', text)))


def sentence_to_name(text):
    return '_'.join([re.sub(r'\W+', '', t).lower() for t in text.split()])


def strip_lines(lines):
    return list(filter(None, map(str.strip, lines)))


def extract_name(test_class_name):
    return test_class_name[4:] if test_class_name.startswith('Test') else test_class_name
