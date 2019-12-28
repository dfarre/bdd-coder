import importlib
import os
import re
import shutil
import subprocess
import unittest
import unittest.mock as mock

from bdd_coder import BASE_TEST_CASE_NAME
from bdd_coder import BASE_TESTER_NAME

from bdd_coder import stock

from bdd_coder.exceptions import (
    BaseModuleNotFoundError, BaseTesterNotFoundError, StoriesModuleNotFoundError,
    Flake8Error)

from bdd_coder.coder import coders

PYTEST_OUTPUT = """
============================= test session starts ==============================
platform linux -- Python [L1-4]
collecting ... collected 2 items

tmp/generated/test_stories.py::ClearBoard::test_odd_boards PASSED        [ 50%]
tmp/generated/test_stories.py::ClearBoard::test_start_board PASSED       [100%]

============================== 2 passed in 0.05s ===============================
""".strip('\n')


class BlueprintTester(unittest.TestCase):
    kwargs = dict(specs_path='example/specs/', tests_path='tmp/generated/',
                  logs_parent='example/tests/')
    base_class = None

    @classmethod
    def setUpClass(cls):
        cls.coder = coders.PackageCoder(**{
            **cls.kwargs, **({'base_class': cls.base_class} if cls.base_class else {})})

        with mock.patch('sys.stdout.write') as stdout_mock:
            cls.coder.create_tester_package()
            cls.coder_output = ''.join([
                line for (line,), kw in stdout_mock.call_args_list])

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree('tmp')

    def assert_test_files_match(self, path):
        py_file_names = ['__init__.py', 'aliases.py', 'base.py', 'test_stories.py']

        assert not set(py_file_names) - set(os.listdir(self.coder.tests_path))
        assert [str(stock.Process('diff', f'tmp/generated/{name}', os.path.join(path, name)))
                for name in py_file_names] == ['']*len(py_file_names)


class CoderTests(BlueprintTester):
    def test_pytest_output(self):
        lines = self.coder_output.splitlines()
        output = '\n'.join([lines[0], 'platform linux -- Python [L1-4]'] + lines[5:])

        assert re.sub(r'[0-9]{2}s', '05s', output) == PYTEST_OUTPUT

    def test_no_pending(self):
        assert subprocess.run([
            'bdd-pending-scenarios', self.coder.logs_parent]).returncode == 0

    def test_pass_flake8(self):
        subprocess.check_output(['flake8', self.coder.tests_path])

    def test_example_test_files_match(self):
        self.assert_test_files_match('example/tests')


class CoderCustomBaseTests(BlueprintTester):
    base_class = 'my.module.path.MyTestCase'

    def test_base_test_case_bases(self):
        with open(os.path.join(self.coder.tests_path, 'base.py')) as py_file:
            source = py_file.read()

        regex = rf'class {BASE_TEST_CASE_NAME}\(MyTestCase, tester\.BaseTestCase\)'

        assert len(re.findall(regex, source)) == 1


class StoriesModuleNotFoundErrorRaiseTest(unittest.TestCase):
    def test_cannot_import(self):
        with self.assertRaises(StoriesModuleNotFoundError) as cm:
            coders.get_base_tester(test_module_path='foo.bar')

        assert str(cm.exception) == 'Test module foo.bar not found'


class PatcherTester(BlueprintTester):
    @property
    def patcher(self):
        return coders.PackagePatcher(
            specs_path='example/new_specs', test_module='tmp.generated.test_stories')


class PatcherTests(PatcherTester):
    def test_split_str(self):
        with open('tests/base_split.json') as json_file:
            assert str(self.patcher.splits['base']) == json_file.read().strip()

    def test_new_example_test_files_match(self):
        self.patcher.patch()

        self.assert_test_files_match('example/new_tests')


class Flake8ErrorRaiseTest(PatcherTester):
    def test_flake8_error(self):
        with open('tmp/generated/test_stories.py') as py_file:
            source = py_file.read()

        with open('tmp/generated/test_stories.py', 'w') as py_file:
            py_file.write(re.sub(
                r'    @decorators.Scenario\(base.steps\)\n    def even_boards',
                lambda m: '\n' + m.group(), re.sub(
                    'class NewGame', lambda m: '\n' + m.group(), source, 1), 1))

        with self.assertRaises(Flake8Error) as cm:
            self.patcher

        assert str(cm.exception) == (
            'tmp/generated/test_stories.py:7:1: E303 too many blank lines (3)\n'
            'tmp/generated/test_stories.py:23:5: E303 too many blank lines (2)\n')


MODULE_TEXT = ("<module 'tmp.generated.test_stories' from "
               "'/home/coleopter/src/bdd-coder/tmp/generated/test_stories.py'>")


class BaseTesterNotFoundErrorRaiseTest(PatcherTester):
    def test_base_tester_not_found_error(self):
        test_module = 'tmp.generated.test_stories'
        del importlib.import_module(test_module).base.BddTester

        with self.assertRaises(BaseTesterNotFoundError) as cm:
            coders.get_base_tester(test_module_path=test_module)

        assert str(cm.exception) == (
            f'Imported base test module {MODULE_TEXT}.base should have a single '
            f'{BASE_TESTER_NAME} subclass - found set()')


class BaseModuleNotFoundErrorRaiseTest(PatcherTester):
    def test_base_module_not_found_error(self):
        test_module = 'tmp.generated.test_stories'
        del importlib.import_module(test_module).base

        with self.assertRaises(BaseModuleNotFoundError) as cm:
            coders.get_base_tester(test_module_path=test_module)

        assert str(cm.exception) == (
            f'Test module {MODULE_TEXT} should have a `base` module imported')
