from __future__ import annotations

import abc

from collections import OrderedDict

import itertools
import subprocess
import sys

from typing import Callable, Iterable, Iterator


class Repr(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def __str__(self) -> str:
        """Object's text content"""

    def __repr__(self):
        return f'<{self.__class__.__name__}: {self}>'


class Eq(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def eq(self, other):
        """Return self == other for same type"""

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False

        return self.eq(other)

    def __ne__(self, other):
        return not self.__eq__(other)


class Hashable(Eq, metaclass=abc.ABCMeta):
    def __hash__(self):
        return hash(self.eqkey())

    @abc.abstractmethod
    def eqkey(self):
        """Return hashable, frozen property to compare to others"""

    def eq(self, other) -> bool:
        return self.eqkey() == other.eqkey()


class SubclassesMixin:
    @classmethod
    def subclasses_down(cls):
        clss, subclasses = [cls], []

        def chain_subclasses(classes):
            return list(itertools.chain(*map(lambda k: k.__subclasses__(), classes)))

        while clss:
            clss = chain_subclasses(clss)
            subclasses.extend(clss)

        return OrderedDict([(sc, list(sc.__bases__)) for sc in subclasses])


class Process(subprocess.Popen):
    def __init__(self, *command, **kwargs):
        super().__init__(command, stdout=subprocess.PIPE, **kwargs)

    def __str__(self) -> str:
        return ''.join(list(self))

    def __iter__(self) -> Iterator[str]:
        line = self.next_stdout()

        while line:
            yield line

            line = self.next_stdout()

    def next_stdout(self) -> str:
        return self.stdout.readline().decode()

    def write(self, stream=sys.stdout):
        for line in self:
            stream.write(line)


class SetPair(Repr):
    def __init__(self, lset: Iterable, rset: Iterable, lname: str = 'l', rname: str = 'r'):
        self.lset, self.rset = set(lset), set(rset)
        self.lname, self.rname = lname, rname

    def __str__(self) -> str:
        return f'{self.lname} {self.symbol} {self.rname}: ' + ' | '.join(
            list(map(lambda s: '{' + ', '.join(sorted(map(repr, s))) + '}' if s else 'ø',
                     self.partition)))

    @property
    def partition(self) -> tuple[set, set, set]:
        return (self.lset - self.rset, self.lset & self.rset, self.rset - self.lset)

    @property
    def partition_map(self) -> dict[str, set]:
        parts = {}
        parts['l-r'], parts['l&r'], parts['r-l'] = self.partition
        return parts

    @property
    def symbol(self) -> str:
        parts = self.partition_map

        if not parts['l-r'] and not parts['r-l']:
            return '='
        elif not parts['l&r']:
            return '⪥'
        elif parts['l-r'] and parts['r-l']:
            return '⪤'
        elif not parts['l-r']:
            return '⊂'
        elif not parts['r-l']:
            return '⊃'
        else:
            raise AssertionError


def list_drop_duplicates(iterable: Iterable, keylambda: Callable) -> list:
    elements: list = []
    keys: list[str] = []

    for e in filter(lambda x: keylambda(x) not in keys, iterable):
        keys.append(keylambda(e))
        elements.append(e)

    return elements
