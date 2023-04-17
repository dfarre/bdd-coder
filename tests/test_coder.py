import importlib
import os
import re
import shutil
import subprocess
import unittest
import unittest.mock as mock

from bdd_coder.text_utils import BASE_TESTER_NAME, assert_test_files_match

from bdd_coder.exceptions import (
    BaseModuleNotFoundError, BaseTesterNotFoundError, StoriesModuleNotFoundError,
    Flake8Error, ScenarioMismatchError)

from bdd_coder import coders

PYTEST_OUTPUT = """
============================= test session starts ==============================
platform linux -- Python [L1-4]
plugins: asyncio-0.21.0, cov-4.0.0
asyncio: mode=strict
collecting ... collected 2 items

tmp/generated/test_stories.py::TestClearBoard::test_odd_boards[9] PASSED [ 50%]
tmp/generated/test_stories.py::TestClearBoard::test_start_board[8] ERROR [100%]

==================================== ERRORS ====================================
_____________ ERROR at setup of TestClearBoard.test_start_board[8] _____________
""".strip()


class BlueprintTester(unittest.TestCase):
    kwargs = dict(specs_path='example/specs', tests_path='tmp/generated',
                  logs_path='example/tests/bdd_runs.log')

    def setUp(self):
        self.coder = coders.PackageCoder(**self.kwargs)

        with mock.patch('sys.stdout.write') as stdout_mock:
            self.coder.create_tester_package(run_pytest=True)

        self.coder_output = ''.join([
            line for (line,), kw in stdout_mock.call_args_list])

    def tearDown(self):
        shutil.rmtree('tmp')


class CoderTests(BlueprintTester):
    def test_pytest_output(self):
        lines = self.coder_output.splitlines()
        output = '\n'.join([lines[0], 'platform linux -- Python [L1-4]'] + lines[5:14])

        assert output == PYTEST_OUTPUT
        assert lines[19] == "E       fixture 'guess_count' not found"

    def test_pass_flake8(self):
        try:
            subprocess.check_output(['flake8', self.coder.tests_path])
        except subprocess.CalledProcessError as error:  # NO COVER
            self.fail(error.stdout.decode())

    def test_example_test_files_match(self):
        assert_test_files_match('example/tests', 'tmp/generated')


class StoriesModuleNotFoundErrorRaiseTest(unittest.TestCase):
    def test_cannot_import(self):
        with self.assertRaises(StoriesModuleNotFoundError) as cm:
            coders.get_base_tester(test_module_path='foo.bar')

        assert str(cm.exception) == 'Test module foo.bar not found'


class PatcherTester(BlueprintTester):
    def get_patcher(self, test_module='tmp.generated.test_stories',
                    specs_path='example/new_specs'):
        return coders.PackagePatcher(test_module=test_module, specs_path=specs_path)


class PatcherTests(PatcherTester):
    def setUp(self):
        super().setUp()
        self.patcher = self.get_patcher()
        self.patcher.patch(run_pytest=True)

    def test_split_str(self):
        with open('tests/base_split.txt') as txt_file:
            assert str(self.patcher.splits['base']) == txt_file.read().strip('\n')

    def test_new_example_test_files_match(self):
        assert_test_files_match('example/new_tests', 'tmp/generated')


class Flake8ErrorRaiseTest(PatcherTester):
    def test_flake8_error(self):
        abspath = os.path.abspath('tmp/generated/test_stories.py')

        with open(abspath) as py_file:
            source = py_file.read()

        with open(abspath, 'w') as py_file:
            py_file.write(re.sub(
                r'    @base.scenario()\n    def even_boards', lambda m: '\n' + m.group(),
                re.sub('class NewGame', lambda m: '\n' + m.group(), source, 1), 1))

        with self.assertRaises(Flake8Error):
            self.get_patcher()


class ScenarioMismatchErrorRaiseTest(PatcherTester):
    def test_scenario_mismatch_error(self):
        with self.assertRaises(ScenarioMismatchError) as cm:
            self.get_patcher('example.wrong_tests.test_stories_odd_scenario')

        assert str(cm.exception).startswith('Scenario code not understood')


MODULE_TEXT = ("<module 'tmp.generated.test_stories' from '" +
               os.path.dirname(os.path.dirname(os.path.abspath(__file__))) +
               "/tmp/generated/test_stories.py'>")


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
