import importlib
import os
import re
import shutil
import subprocess
import unittest
import unittest.mock as mock

from bdd_coder import commands

from bdd_coder.coder import coders

PYTEST_OUTPUT = """
============================= test session starts ==============================
platform linux -- Python [L1-4]
collecting ... collected 2 items

tmp/generated/test_stories.py::ClearBoard::test_odd_boards PASSED        [ 50%]
tmp/generated/test_stories.py::ClearBoard::test_start_board PASSED       [100%]

=========================== 2 passed in 0.05 seconds ===========================
""".strip('\n')


class BlueprintTester(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.coder = coders.PackageCoder(
            specs_path='example/specs/', tests_path='tmp/generated/',
            logs_parent='example/tests/')

        with mock.patch('sys.stdout.write') as stdout_mock:
            cls.coder.create_tester_package()

            assert stdout_mock.call_count == 11

            cls.coder_output = ''.join([
                line for (line,), kw in stdout_mock.call_args_list])

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree('tmp')

    def assert_test_files_match(self, path):
        py_file_names = ['__init__.py', 'aliases.py', 'base.py', 'test_stories.py']

        assert not set(py_file_names) - set(os.listdir(self.coder.tests_path))
        assert [subprocess.run(['diff', f'tmp/generated/{name}', os.path.join(path, name)],
                               stdout=subprocess.PIPE).stdout.decode()
                for name in py_file_names] == ['']*len(py_file_names)


class CoderTester(BlueprintTester):
    def test_pytest_output(self):
        lines = self.coder_output.splitlines()
        output = '\n'.join([lines[0], 'platform linux -- Python [L1-4]'] + lines[5:])

        assert re.sub(r'[0-9]{2} seconds', '05 seconds', output) == PYTEST_OUTPUT

    def test_no_pending(self):
        assert commands.CheckPendingScenarios(test_mode=True)(
            logs_parent=self.coder.logs_parent) == 0

    def test_pass_flake8(self):
        try:
            subprocess.check_output(['flake8', self.coder.tests_path])
        except subprocess.CalledProcessError as error:
            self.fail(error.output.decode())

    def test_example_test_files_match(self):
        self.assert_test_files_match('example/tests')

    def test_class_tree(self):
        assert not importlib.import_module('tmp.generated.base').BddTester.validate_bases(
            self.coder.features_spec)


class PatcherTester(BlueprintTester):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.patcher = coders.PackagePatcher(
            specs_path='example/new_specs', test_module='tmp.generated.test_stories')
        cls.patcher.patch()

    def test_split_str(self):
        with open('tests/base_split.json') as json_file:
            assert str(self.patcher.split('base')) == json_file.read().strip()

    def test_new_example_test_files_match(self):
        self.assert_test_files_match('example/new_tests')
