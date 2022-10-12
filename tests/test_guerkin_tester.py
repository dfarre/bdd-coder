import os
import subprocess
import unittest


class GherkinTesterTests(unittest.TestCase):
    pytest_outputs_dir = 'tests'

    def assert_pytest_fails(self, example_path):
        with self.assertRaises(subprocess.CalledProcessError) as cm:
            subprocess.check_output(['pytest',
                                     '-vv',
                                     '--log-level=5',
                                     '--log-format=%(message)s',
                                     f'example/{example_path}'])
        return cm

    def assert_collection_error(self, example_path):
        output = self.assert_pytest_fails(example_path).exception.output.decode()

        assert f'ERROR collecting example/{example_path}' in output

        return output

    def assert_pytest_failure_output(self, package_name):
        cm = self.assert_pytest_fails(package_name)
        assert cm.exception.returncode == 1, cm.exception.output.decode()
        log_path = os.path.join(self.pytest_outputs_dir, f'{package_name}.pytest_output')

        # FIXME IF not commented out, in order to freeze the files and do real tests
        # with open(log_path, 'w') as log_file:
        #     log_file.write(cm.exception.output.decode())

        with open(log_path) as output_file:
            assert output_file.read() == cm.exception.output.decode()

    def test_parameter_collection(self):
        self.assert_pytest_failure_output('advanced_tests')

    def test_redeclared_parameter_exception(self):
        output = self.assert_collection_error('wrong_tests/test_stories_redeclared_param.py')

        assert 'RedeclaredParametersError: Redeclared parameter(s) n' in output

    def test_redeclared_parameter_in_same_scenario(self):
        output = self.assert_collection_error('wrong_tests/test_stories_repeated_param.py')

        assert 'RedeclaredParametersError: Redeclared parameter(s) n' in output

    def test_wrong_param_values_exception(self):
        output = self.assert_collection_error('wrong_tests/test_stories_wrong_param_values.py')

        assert ('Invalid parameters at positions 0, 1 in scenario test_start_board: '
                'should be lists of length 2 (number of parameters declared in doc)' in output)
