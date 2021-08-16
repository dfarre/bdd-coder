"""Common utils and constants"""
import os
import re
import sys
import traceback

from pygments import highlight
from pygments.lexers.python import PythonTracebackLexer
from pygments.formatters import TerminalFormatter

from bdd_coder import stock

BASE_TESTER_NAME = 'BddTester'

COMPLETION_MSG = 'All scenarios ran!'
OK, FAIL, PENDING, TO = '✔', '✖', '❓', '↦'
BOLD = {OK: '✅', FAIL: '❌'}

PARAM_REGEX = r'\$([a-zA-Z_]+)'
I_REGEX = r'\$\(([^\$]+)\)'
O_REGEX = r'`([^`\$]+)`'


class Style:
    end_mark = '\033[0m'

    @classmethod
    def purple(cls, text):
        return '\033[95m' + text + cls.end_mark

    @classmethod
    def dark_cyan(cls, text):
        return '\033[36m' + text + cls.end_mark

    @classmethod
    def cyan(cls, text):
        return '\033[96m' + text + cls.end_mark

    @classmethod
    def blue(cls, text):
        return '\033[94m' + text + cls.end_mark

    @classmethod
    def green(cls, text):
        return '\033[92m' + text + cls.end_mark

    @classmethod
    def yellow(cls, text):
        return '\033[93m' + text + cls.end_mark

    @classmethod
    def red(cls, text):
        return '\033[91m' + text + cls.end_mark

    @classmethod
    def bold(cls, text):
        return '\033[1m' + text + cls.end_mark

    @classmethod
    def underline(cls, text):
        return '\033[1m' + text + cls.end_mark


class ExcInfo:
    def __init__(self):
        self.exc_type, self.exc_value, self.tb = sys.exc_info()

    @property
    def next_traceback(self):
        text = ''.join(traceback.format_list(traceback.extract_tb(self.tb.tb_next)))

        return ('Traceback (most recent call last):\n'
                f'{text}{self.exc_type.__qualname__}: {self.exc_value}\n')

    @property
    def highlighted_traceback(self):
        return highlight(
            self.next_traceback, PythonTracebackLexer(), TerminalFormatter())


def to_sentence(name):
    return name.replace('_', ' ').capitalize()


def sentence_to_name(text):
    return '_'.join([re.sub(r'\W+', '', t).lower() for t in text.split()])


def strip_lines(lines):
    return list(filter(None, map(str.strip, lines)))


def extract_name(test_class_name):
    return test_class_name[4:] if test_class_name.startswith('Test') else test_class_name


def indent(text, tabs=1):
    newspace = ' '*4*tabs
    text = text.replace('\n', '\n' + newspace)

    return newspace + text


def make_doc(*lines):
    text = '\n'.join(line.strip() for line in lines)

    return f'"""\n{text}\n"""' if text else ''


def decorate(target, decorators):
    return '\n'.join([f'@{decorator}' for decorator in decorators] + [target])


def make_def_content(*doc_lines, body=''):
    return indent('\n'.join(([make_doc(*doc_lines)] if doc_lines else []) +
                            ([body] if body else []) or ['pass']))


def make_class_head(name, bases=(), decorators=()):
    inheritance = f'({", ".join(map(str.strip, bases))})' if bases else ''

    return decorate(f'class {name}{inheritance}', decorators)


def make_class(name, *doc_lines, bases=(), decorators=(), body=''):
    return '\n'.join([f'{make_class_head(name, bases, decorators)}:',
                      make_def_content(*doc_lines, body=body)])


def make_method(name, *doc_lines, args_text='', decorators=(), body=''):
    return '\n'.join([decorate(f'def {name}(self{args_text}):', decorators),
                      make_def_content(*doc_lines, body=body)])


def rstrip(text):
    return '\n'.join(list(map(str.rstrip, text.splitlines()))).lstrip('\n')


def assert_test_files_match(origin_dir, target_dir):
    py_file_names = ['__init__.py', 'aliases.py', 'base.py', 'test_stories.py']
    missing_in_origin = set(py_file_names) - set(os.listdir(origin_dir))
    missing_in_target = set(py_file_names) - set(os.listdir(target_dir))

    assert not missing_in_origin, f'Missing in {origin_dir}: {missing_in_origin}'
    assert not missing_in_target, f'Missing in {target_dir}: {missing_in_target}'

    diff_lines = {name: str(stock.Process(
        'diff', os.path.join(origin_dir, name), os.path.join(target_dir, name)
    )) for name in py_file_names}

    assert list(diff_lines.values()) == ['']*len(py_file_names), '\n'.join([
        f'Diff from {os.path.join(origin_dir, name)}:\n{diff}'
        for name, diff in diff_lines.items() if diff])
