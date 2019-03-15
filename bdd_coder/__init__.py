"""Common utils and constants"""

import collections
import itertools
import re

LOGS_DIR_NAME = '.bdd-run-logs'
OK_SMALL, OK_BIG = '✓', '✅'
FAIL_SMALL, FAIL_BIG = '✗', '❌'
COMPLETION_MSG = 'All scenarios ran'


class Repr:
    def __str__(self):
        raise NotImplementedError

    def __repr__(self):
        return f'<{self.__class__.__name__}: {self}>'


class SubclassesMixin:
    @classmethod
    def subclasses_down(cls):
        clss, subclasses = [cls], []

        def chain_subclasses(classes):
            return list(itertools.chain(*map(lambda k: k.__subclasses__(), classes)))

        while clss:
            clss = chain_subclasses(clss)
            subclasses.extend(clss)

        return collections.OrderedDict([(sc, list(sc.__bases__)) for sc in subclasses])


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
