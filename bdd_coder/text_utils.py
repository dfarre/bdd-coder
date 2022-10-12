"""Common utils and constants"""
from __future__ import annotations

import os
import re
import sys
import traceback

from typing import Iterable

from pygments import highlight
from pygments.lexers.python import PythonTracebackLexer
from pygments.formatters import TerminalFormatter

from bdd_coder import stock

BASE_TESTER_NAME: str = 'BddTester'

COMPLETION_MSG: str = 'All scenarios ran!'
OK: str = '✔'
FAIL: str = '✖'
PENDING: str = '❓'
TO: str = '↦'
BOLD: dict[str, str] = {OK: '✅', FAIL: '❌'}

PARAM_REGEX: str = r'\$([a-zA-Z_]+)'
I_REGEX: str = r'\$\(([^\$]+)\)'
O_REGEX: str = r'`([^`\$]+)`'


class Style:
    end_mark = '\033[0m'

    @classmethod
    def bold(cls, text: str) -> str:
        return '\033[1m' + text + cls.end_mark

    @classmethod
    def purple(cls, text: str) -> str:  # NO COVER: not in use
        return '\033[95m' + text + cls.end_mark

    @classmethod
    def dark_cyan(cls, text: str) -> str:  # NO COVER: not in use
        return '\033[36m' + text + cls.end_mark

    @classmethod
    def cyan(cls, text: str) -> str:  # NO COVER: not in use
        return '\033[96m' + text + cls.end_mark

    @classmethod
    def blue(cls, text: str) -> str:  # NO COVER: not in use
        return '\033[94m' + text + cls.end_mark

    @classmethod
    def green(cls, text: str) -> str:  # NO COVER: not in use
        return '\033[92m' + text + cls.end_mark

    @classmethod
    def yellow(cls, text: str) -> str:  # NO COVER: not in use
        return '\033[93m' + text + cls.end_mark

    @classmethod
    def red(cls, text: str) -> str:  # NO COVER: not in use
        return '\033[91m' + text + cls.end_mark

    @classmethod
    def underline(cls, text: str) -> str:  # NO COVER: not in use
        return '\033[1m' + text + cls.end_mark


class ExcInfo:
    def __init__(self):
        self.exc_type, self.exc_value, self.tb = sys.exc_info()

    @property
    def next_traceback(self) -> str:
        text = ''.join(traceback.format_list(traceback.extract_tb(self.tb.tb_next)))

        return ('Traceback (most recent call last):\n'
                f'{text}{self.exc_type.__qualname__}: {self.exc_value}\n')

    @property
    def highlighted_traceback(self) -> str:
        return highlight(
            self.next_traceback, PythonTracebackLexer(), TerminalFormatter())


def to_sentence(name: str) -> str:
    return name.replace('_', ' ').capitalize()


def sentence_to_name(text: str) -> str:
    return '_'.join([re.sub(r'\W+', '', t).lower() for t in text.split()])


def strip_lines(lines: list[str]) -> list[str]:
    return list(filter(None, map(str.strip, lines)))


def extract_name(test_class_name: str) -> str:
    return test_class_name[4:] if test_class_name.startswith('Test') else test_class_name


def indent(text: str, tabs: int = 1) -> str:
    newspace = ' '*4*tabs
    text = text.replace('\n', '\n' + newspace)

    return newspace + text


def make_doc(*lines) -> str:
    text = '\n'.join(line.strip() for line in lines)

    return f'"""\n{text}\n"""' if text else ''


def decorate(target: str, decorators: Iterable[str]):
    return '\n'.join([f'@{decorator}' for decorator in decorators] + [target])


def make_def_content(*doc_lines, body='', upper_blank_line=True):
    sep = '\n\n' if upper_blank_line else '\n'
    return indent(sep.join(([make_doc(*doc_lines)] if doc_lines else []) +
                           ([body.strip()] if body.strip() else []) or ['pass']))


def make_class_head(name: str, bases: Iterable[str] = (), decorators: Iterable[str] = ()):
    inheritance = f'({", ".join(map(str.strip, bases))})' if bases else ''

    return decorate(f'class {name}{inheritance}', decorators)


def make_class(name: str, *doc_lines, bases: Iterable[str] = (), decorators: Iterable[str] = (),
               body: str = '', upper_blank_line: bool = True):
    return '\n'.join([f'{make_class_head(name, bases, decorators)}:',
                      make_def_content(*doc_lines, body=body, upper_blank_line=upper_blank_line)])


def make_method(name: str, *doc_lines, args_text: str = 'self', decorators: Iterable[str] = (),
                body: str = '', upper_blank_line: bool = True) -> str:
    return '\n'.join([decorate(f'def {name}({args_text}):', decorators),
                      make_def_content(*doc_lines, body=body,
                                       upper_blank_line=upper_blank_line)])


def rstrip(text: str) -> str:
    return '\n'.join(list(map(str.rstrip, text.splitlines()))).lstrip('\n')


def assert_test_files_match(origin_dir: str, target_dir: str):
    py_file_names = ['__init__.py', 'base.py', 'test_stories.py']
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
