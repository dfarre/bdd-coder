import shutil
import subprocess
import unittest

from bdd_coder.coder import coders


class BlueprintTester(unittest.TestCase):
    def setUp(self):
        self.coder = coders.Coder(
            specs_path='tests/example_specs', tests_path='tests/example_tests')

    def test_created_package(self):
        self.coder.create_tester_package()

        try:
            subprocess.check_output(['pytest', self.coder.tests_path])
        except subprocess.CalledProcessError as error:
            self.fail(error.output.decode())

    def tearDown(self):
        shutil.rmtree(self.coder.tests_path)
