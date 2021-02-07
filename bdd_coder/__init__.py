"""Common utils and constants"""
import re

BASE_TEST_CASE_NAME = 'BaseTestCase'
BASE_TESTER_NAME = 'BddTester'

COMPLETION_MSG = 'All scenarios ran'
OK, FAIL, TO = '✅', '❌', '↦'

PARAM_REGEX = r'[^"`\$]+'
I_REGEX = rf'"({PARAM_REGEX})"'
O_REGEX = rf'`({PARAM_REGEX})`'
FIXTURE_REGEX = r'\$[a-zA-Z_]\w*'


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
