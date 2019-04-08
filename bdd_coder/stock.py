import abc
import argparse
import collections
import configparser
import inspect
import itertools
import os
import shutil
import subprocess
import sys

from packaging import version


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


class VersionFile(Repr, ParametersMixin):
    qualifiers = ('pre', 'post', 'dev')

    def __init__(self, path='version.ini'):
        self.ini = configparser.ConfigParser()
        self.ini.read(path)
        self.path = path

    def __str__(self):
        return f'{self.name}-{self.v}'

    @property
    def v(self):
        return version.Version(self.ini['version']['value'])

    @property
    def name(self):
        return self.ini['version']['name']

    def put(self, text, key='value'):
        self.ini['version'][key] = text

        with open(self.path, 'w') as wfile:
            self.ini.write(wfile)

    def up(self, *inc):
        """Shifts version and prunes qualifiers"""
        release, inc = self.v.release, list(map(int, inc))
        head, tail = inc[:len(release)], inc[len(release):]

        if not tail and len(release) > len(head):
            head = [0]*(len(release) - len(head)) + head

        self.put('.'.join(map(str, list(map(sum, zip(release, head))) + tail)))

    def qualify(self, **incs):
        current = dict(map(
            lambda it: (it[0], it[1][1] if isinstance(it[1], tuple) else it[1]),
            filter(lambda it: it[1] is not None, (
                (key, getattr(self.v, key)) for key in self.qualifiers))))
        quals = '.'.join([
            f'{key}{current.get(key, -1) + incs.get(key, 0)}'
            for key in self.qualifiers if key in set(current) | set(incs)])
        self.put(f'{self.v.base_version}.{quals}')


class Command(metaclass=abc.ABCMeta):
    arguments = ()

    def __init__(self, test_mode=False):
        if not test_mode:
            self.parser = argparse.ArgumentParser()

            for args, kwargs in self.arguments:
                self.parser.add_argument(*args, **kwargs)

        self.test_mode = test_mode

    def __call__(self, **kwargs):
        items = kwargs.items() if self.test_mode else self.parser.parse_args()._get_kwargs()

        return self.call(**{key: value for key, value in items if value is not None})

    @abc.abstractmethod
    def call(self, **kwargs):
        """The command function"""


class ErrorsCommand(Command, metaclass=abc.ABCMeta):
    exceptions = ()

    @abc.abstractmethod
    def try_call(self, **kwargs):
        f"""May raise {self.exceptions}"""

    def finally_call(self, **kwargs):
        """Final clean up"""

    def call(self, **kwargs):
        try:
            self.try_call(**kwargs)
            return 0
        except self.exceptions as error:
            sys.stderr.write(str(error) + '\n')
            return 1
        finally:
            self.finally_call(**kwargs)


class ToPyPI(ErrorsCommand):
    params = VersionFile.get_parameters()
    arguments = (
        (('inc',), dict(nargs='*', type=int, help='Version number increments (0s left)')),
        (('--test-pypi',), dict(action='store_true', help='Use test.pypi.org')), *(
            ((f'--{qal}',), dict(type=int, help='Qualifier increment'))
            for qal in VersionFile.qualifiers))
    exceptions = (FileNotFoundError, subprocess.CalledProcessError)

    @staticmethod
    def check_output(*cmd):
        sys.stdout.write(subprocess.check_output(cmd).decode())

    @staticmethod
    def upload_cmd(config, test_pypi):
        return ['twine', 'upload', '-u', config['user'], '-p',
                config['test_password'] if test_pypi else config['password']
                ] + (['--repository-url', 'https://test.pypi.org/legacy/']
                     if test_pypi else []) + ['dist/*']

    def try_call(self, **kwargs):
        version_file, inc = VersionFile(), kwargs.pop('inc')
        test_pypi = kwargs.pop('test_pypi')

        if inc:
            version_file.up(*inc)

        if kwargs:
            version_file.qualify(**kwargs)

        if os.path.isdir('dist'):
            shutil.rmtree('dist')

        self.check_output('python', 'setup.py', 'sdist', 'bdist_wheel')
        secrets = configparser.ConfigParser()
        secrets.read('.secrets.ini')

        if test_pypi:
            self.check_output(*self.upload_cmd(secrets['pypi'], test_pypi))
        else:
            go, choices = '', {'Yes': True, 'No': False}

            while not (go in choices):
                go = input(f'Upload {version_file} to PyPI ({"/".join(choices)})? ')

            if choices[go]:
                self.check_output(*self.upload_cmd(secrets['pypi'], test_pypi))
            else:
                sys.stdout.write('Aborted\n')


class SetPair(Repr):
    def __init__(self, lset, rset, lname='l', rname='r'):
        self.lset, self.rset = set(lset), set(rset)
        self.lname, self.rname = lname, rname

    def __str__(self):
        return f'{self.lname} {self.symbol} {self.rname}: ' + ' | '.join(
            list(map(lambda s: '{' + ', '.join(sorted(map(repr, s))) + '}' if s else 'ø',
                     self.partition)))

    @property
    def partition(self):
        return [self.lset - self.rset, self.lset & self.rset, self.rset - self.lset]

    @property
    def symbol(self):
        parts = {}
        parts['l-r'], parts['l&r'], parts['r-l'] = self.partition

        if not parts['l&r']:
            return '⪥'
        elif not parts['l-r'] and not parts['r-l']:
            return '='
        elif parts['l-r'] and parts['r-l']:
            return '⪤'
        elif not parts['l-r']:
            return '⊂'
        elif not parts['r-l']:
            return '⊃'
