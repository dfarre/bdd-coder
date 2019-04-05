"""Common utils and constants"""

import re

BASE_TEST_CASE_NAME = 'BaseTestCase'
BASE_TESTER_NAME = 'BddTester'

LOGS_DIR_NAME = '.bdd-run-logs'
COMPLETION_MSG = 'All scenarios ran'
OK, FAIL = '✅', '❌'


def get_step_sentence(step_text):
    return step_text.strip().split(maxsplit=1)[1].strip()


def sentence_to_name(text):
    return re.sub(r'[\'`]|"[\w\-\.]+"', '', text).lower().replace(' ', '_')


def strip_lines(lines):
    return list(filter(None, map(str.strip, lines)))


def get_spec(sentence, aliases=None):
    aliases = aliases or {}
    inputs = re.findall(r'"([\w\-\.]+)"', sentence)
    output_names = re.findall(r'`([\w\-\.]+)`', sentence)
    method = sentence_to_name(sentence)

    return [aliases.get(method, method), inputs, output_names]


def get_step_specs(lines, aliases):
    return [get_spec(get_step_sentence(line), aliases) for line in strip_lines(lines)]


def to_sentence(name):
    return name.replace('__', ' "x" ').replace('_', ' ').capitalize()
