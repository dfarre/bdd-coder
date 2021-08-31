import subprocess
import unittest

PYTEST_OUTPUT = """
============================= test session starts ==============================
platform linux -- Python [L1-4]
collecting ... collected 5 items

example/advanced_tests/test_stories.py::TestClearBoard::test_odd_boards[9] FAILED [ 20%]
example/advanced_tests/test_stories.py::TestClearBoard::test_start_board[Goat-8-Boring-9] PASSED [ 40%]
example/advanced_tests/test_stories.py::TestClearBoard::test_start_board[Cat-6-Funny-11] PASSED [ 60%]
example/advanced_tests/test_stories.py::TestClearBoard::test_start_colored_board[0-Red-8-Boring-9] PASSED [ 80%]
example/advanced_tests/test_stories.py::TestClearBoard::test_start_colored_board[1-Green-6-Funny-11] PASSED [100%]
""".lstrip()  # noqa


class GherkinTesterTests(unittest.TestCase):
    def assert_pytest_fails(self, example_path):
        with self.assertRaises(subprocess.CalledProcessError) as cm:
            subprocess.check_output(['pytest', '-v', f'example/{example_path}'])

        return cm.exception.output.decode()

    def assert_collection_error(self, example_path):
        output = self.assert_pytest_fails(example_path)

        assert f'ERROR collecting example/{example_path}' in output

        return output

    def test_parameter_collection(self):
        output = self.assert_pytest_fails('advanced_tests')
        print(output)
        lines = output.splitlines()
        cut_output = '\n'.join([lines[0], 'platform linux -- Python [L1-4]'] + lines[5:13])

        assert cut_output == PYTEST_OUTPUT

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
