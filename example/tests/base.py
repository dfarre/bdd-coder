from unittest import TestCase

from bdd_coder.tester import decorators
from bdd_coder.tester import tester

from . import aliases

steps = decorators.Steps(aliases.MAP, 'example/tests/')


@steps
class BddTester(tester.BddTester):
    pass


class BaseTestCase(tester.BaseTestCase, TestCase):
    pass
