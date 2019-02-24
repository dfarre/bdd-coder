import shutil
import subprocess
import unittest

from bdd_coder import commands
from bdd_coder import SUCCESS_MSG

from bdd_coder.coder import coders


class BlueprintTester(unittest.TestCase):
    def setUp(self):
        self.coder = coders.PackageCoder(
            specs_path='tests/example_specs', tests_path='tests/example_tests')

    def test_created_package(self):
        self.coder.create_tester_package()

        try:
            subprocess.check_output(['pytest', '-vv', self.coder.tests_path])
        except subprocess.CalledProcessError as error:
            self.fail(error.output.decode())

        assert commands.check_pending_scenarios(self.coder.tests_path) == SUCCESS_MSG

    def tearDown(self):
        shutil.rmtree(self.coder.tests_path)
