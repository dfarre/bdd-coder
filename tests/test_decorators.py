import datetime
import sys
import unittest
from unittest import mock

import freezegun

from bdd_coder import OK, FAIL, TO, COMPLETION_MSG

from example.tests import base
from example.tests import test_stories

NEW_GAME = 'example.tests.test_stories.NewGame'
CLEAR_BOARD = 'example.tests.test_stories.TestClearBoard'

FROZEN_TIME = datetime.datetime(2019, 3, 18, 17, 30, 13, 71420)
FIRST_LOG = f"""________________________________________________________________________________
1 {OK} NewGame.even_boards:
  1.1 - {FROZEN_TIME} {OK} i_request_a_new_game_with_an_even_number_of_boards [] {TO} ('Even Game',)
  1.2 - {FROZEN_TIME} {OK} a_game_is_created_with_boards_of__guesses ['12'] {TO} ()
2 {OK} TestClearBoard.test_start_board:
  2.1 - {FROZEN_TIME} {OK} even_boards [] {TO} ()
  2.2 - {FROZEN_TIME} {OK} i_request_a_clear_board_in_my_new_game [] {TO} ('Board',)
  2.3 - {FROZEN_TIME} {OK} board__is_added_to_the_game [] {TO} ()
Scenario runs {{
    "1{OK}": "even_boards",
    "2{OK}": "test_start_board"
}}
Pending [
    "test_odd_boards"
]
"""  # noqa: E501
SECOND_LOG = f"""________________________________________________________________________________
3 {OK} NewGame.test_odd_boards:
  3.1 - {FROZEN_TIME} {OK} i_request_a_new_game_with_an_odd_number_of_boards [] {TO} ('Odd Game',)
  3.2 - {FROZEN_TIME} {OK} i_get_a_400_response_saying_it_must_be_even [] {TO} ()
Scenario runs {{
    "1{OK}": "even_boards",
    "2{OK}": "test_start_board",
    "3{OK}": "test_odd_boards"
}}
Pending []
{COMPLETION_MSG} ▌ 3 {OK}
"""  # noqa: E501
FAILURE_LOG_PY36 = f"""{FROZEN_TIME} {FAIL} i_request_a_new_game_with_an_odd_number_of_boards [] {TO} Traceback (most recent call last):
  File "/usr/lib/python3.6/unittest/mock.py", line 939, in __call__
    return _mock_self._mock_call(*args, **kwargs)
  File "/usr/lib/python3.6/unittest/mock.py", line 999, in _mock_call
    raise effect
Exception: FAKE
"""  # noqa: E501
FAILURE_LOG_PY38 = f"""{FROZEN_TIME} {FAIL} i_request_a_new_game_with_an_odd_number_of_boards [] {TO} Traceback (most recent call last):
  File "/usr/lib/python3.8/unittest/mock.py", line 1081, in __call__
    return self._mock_call(*args, **kwargs)
  File "/usr/lib/python3.8/unittest/mock.py", line 1085, in _mock_call
    return self._execute_mock_call(*args, **kwargs)
  File "/usr/lib/python3.8/unittest/mock.py", line 1140, in _execute_mock_call
    raise effect
Exception: FAKE
"""  # noqa: E501
FAILURE_LOG = {6: FAILURE_LOG_PY36, 8: FAILURE_LOG_PY38}[sys.version_info.minor]
SCENARIO_FAIL_LOG = f"""1 {FAIL} NewGame.test_odd_boards:
  1.1 - {FAILURE_LOG}"""


class DecoratorTests(unittest.TestCase):
    logs_path = 'example/tests/bdd_runs.log'

    @classmethod
    def clean_logs(cls):
        with open(cls.logs_path, 'w'):
            pass

    @classmethod
    def setUpClass(cls):
        assert base.steps.scenarios == {
            'test_odd_boards': [], 'even_boards': [], 'test_start_board': []}

    def setUp(self):
        base.steps.run_number = 0
        self.clean_logs()

    def tearDown(self):
        self.clean_logs()

    @mock.patch(f'{NEW_GAME}.i_get_a_400_response_saying_it_must_be_even',
                return_value=None)
    @mock.patch(f'{NEW_GAME}.i_request_a_new_game_with_an_odd_number_of_boards',
                return_value=('Odd Game',))
    def assert_odd_boards(self, odd_mock, error_mock):
        tester = test_stories.TestClearBoard()
        tester.setup_class()
        tester.test_odd_boards()

        odd_mock.assert_called_once_with()
        error_mock.assert_called_once_with()

        tester.teardown_class()

    @mock.patch(f'{NEW_GAME}.i_get_a_400_response_saying_it_must_be_even',
                return_value=None)
    @mock.patch(f'{NEW_GAME}.i_request_a_new_game_with_an_odd_number_of_boards',
                return_value=('Odd Game',), side_effect=Exception('FAKE'))
    def assert_odd_boards__fail(self, odd_mock, error_mock):
        tester = test_stories.TestClearBoard()
        tester.test_odd_boards()

    @mock.patch(f'{CLEAR_BOARD}.board__is_added_to_the_game',
                return_value=None)
    @mock.patch(f'{CLEAR_BOARD}.i_request_a_clear_board_in_my_new_game',
                return_value=('Board',))
    @mock.patch(f'{NEW_GAME}.a_game_is_created_with_boards_of__guesses',
                return_value=None)
    @mock.patch(f'{NEW_GAME}.i_request_a_new_game_with_an_even_number_of_boards',
                return_value=('Even Game',))
    def assert_start_board(self, even_mock, created_mock, clear_board_mock, added_board_mock):
        tester = test_stories.TestClearBoard()
        tester.setup_class()
        tester.test_start_board()

        even_mock.assert_called_once_with()
        created_mock.assert_called_once_with('12')
        clear_board_mock.assert_called_once_with()
        added_board_mock.assert_called_once_with()

        tester.teardown_class()

    def assert_log(self, log_text):
        with open(self.logs_path) as log:
            text = log.read()

        assert text.startswith(log_text), text

    @mock.patch('pytest.fail')
    @freezegun.freeze_time(FROZEN_TIME)
    def test_fail_traceback(self, fail_mock):
        self.assert_odd_boards__fail()

        fail_mock.assert_called_once_with(FAILURE_LOG)
        self.assert_log(SCENARIO_FAIL_LOG)

    @freezegun.freeze_time(FROZEN_TIME)
    def test_calls(self):
        self.assert_start_board()
        assert base.steps.outputs['game'] == ['Even Game']
        assert base.steps.outputs['board'] == ['Board']
        self.assert_log(FIRST_LOG)
        self.assert_odd_boards()
        assert base.steps.outputs['game'] == ['Even Game', 'Odd Game']
        self.assert_log(FIRST_LOG + SECOND_LOG)
        assert list(map(len, base.steps.scenarios.values())) == [1]*len(base.steps.scenarios)
        assert base.steps.scenarios == {
            'even_boards': [(1, OK)], 'test_start_board': [(2, OK)],
            'test_odd_boards': [(3, OK)]}
