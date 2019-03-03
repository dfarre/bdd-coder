import os
import re
import shutil
import subprocess
import unittest

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
        cls.output = cls.coder.create_tester_package()

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree('tmp')

        super().tearDownClass()

    def test_pytest_output(self):
        lines = self.output.splitlines()
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
        file_names = set(os.listdir(self.coder.tests_path))
        py_file_names = {'__init__.py', 'aliases.py', 'base.py', 'test_stories.py'}

        assert not py_file_names - file_names

        for name in py_file_names:
            diff = subprocess.run([
                'diff', f'tmp/generated/{name}', f'example/tests/{name}'],
                stdout=subprocess.PIPE).stdout.decode()

            assert diff == ''
