import os
import shutil
import subprocess
import unittest

from bdd_coder import commands

from bdd_coder.coder import coders


class BlueprintTester(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.coder = coders.PackageCoder(
            specs_path='example/specs/', tests_path='tmp/generated/',
            logs_parent='example/tests/')
        cls.coder.create_tester_package()

    def test_pass_pytest(self):
        try:
            subprocess.check_output(['pytest', '-vv', self.coder.tests_path])
        except subprocess.CalledProcessError as error:
            self.fail(error.output.decode())

        assert commands.check_pending_scenarios(self.coder.tests_path) == 0

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

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree('tmp')

        super().tearDownClass()
