"""Common utils and constants"""

import collections
import inspect
import itertools
import re
import subprocess
import sys

BASE_TEST_CASE_NAME = 'BaseTestCase'
BASE_TESTER_NAME = 'BddTester'

LOGS_DIR_NAME = '.bdd-run-logs'
COMPLETION_MSG = 'All scenarios ran'
OK, FAIL = '✅', '❌'


class Repr:
    def __str__(self):
        raise NotImplementedError

    def __repr__(self):
        return f'<{self.__class__.__name__}: {self}>'


class DocException(Exception):
    def __init__(self, *args, **kwargs):
        self.text = ' '.join(list(filter(None, map(str.strip, self.__doc__.format(
            *args, **kwargs).splitlines()))))

    def __str__(self):
        return self.text


class InconsistentClassStructure(DocException):
    """
    Expected class structure {class_bases_text} from docs
    does not match the defined one. {error}
    """


class BaseTesterRetrievalError(DocException):
    """Raised in the base tester retrieval process"""


class StoriesModuleNotFoundError(BaseTesterRetrievalError):
    """Test module {test_module} not found"""


class BaseModuleNotFoundError(BaseTesterRetrievalError):
    """Test module {test_module} should have a `base` module imported"""


class BaseTesterNotFoundError(BaseTesterRetrievalError):
    """
    Imported base test module {test_module}.base should have a single
    BddTester subclass - found {set}
    """


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


class ParametersMixin:
    @classmethod
    def get_parameters(cls):
        return inspect.signature(cls).parameters


class Process(subprocess.Popen):
    def __init__(self, *command, **kwargs):
        super().__init__(command, stdout=subprocess.PIPE, **kwargs)

    def __str__(self):
        return ''.join(list(self))

    def __iter__(self):
        line = self.next_stdout()

        while line:
            yield line

            line = self.next_stdout()

    def next_stdout(self):
        return self.stdout.readline().decode()

    def write(self, stream=sys.stdout):
        for line in self:
            stream.write(line)


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
