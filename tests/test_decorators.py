import datetime
import os
import shutil
import sys
import unittest
import unittest.mock as mock

import freezegun

from bdd_coder import LOGS_DIR_NAME, OK, FAIL, TO, COMPLETION_MSG

from example.tests import base
from example.tests import test_stories

NEW_GAME = 'example.tests.test_stories.NewGame'
CLEAR_BOARD = 'example.tests.test_stories.ClearBoard'

FROZEN_TIME = datetime.datetime(2019, 3, 18, 17, 30, 13, 71420)
FIRST_LOG = f"""
1 {OK} ClearBoard.even_boards:
  1.1 - {FROZEN_TIME} {OK} i_request_a_new_game_with_an_even_number_of_boards [] {TO} ('Even Game',)
  1.2 - {FROZEN_TIME} {OK} a_game_is_created_with_boards_of__guesses ['12'] {TO} ()

2 {OK} ClearBoard.test_start_board:
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

""".lstrip('\n')  # noqa
SECOND_LOG = f"""
3 {OK} ClearBoard.test_odd_boards:
  3.1 - {FROZEN_TIME} {OK} i_request_a_new_game_with_an_odd_number_of_boards [] {TO} ('Odd Game',)
  3.2 - {FROZEN_TIME} {OK} i_get_a_400_response_saying_it_must_be_even [] {TO} ()

Scenario runs {{
    "1{OK}": "even_boards",
    "2{OK}": "test_start_board",
    "3{OK}": "test_odd_boards"
}}
Pending []

{COMPLETION_MSG} ▌ 3 {OK}

""".lstrip('\n')  # noqa
TRACEBACK = f"""{FROZEN_TIME} {FAIL} i_request_a_new_game_with_an_odd_number_of_boards [] {TO} Traceback (most recent call last):
  File "/usr/lib/python3.{sys.version_info.minor}/unittest/mock.py", line """  # noqa
FAIL_LOG = f"""
4 {FAIL} ClearBoard.test_odd_boards:
  4.1 - {TRACEBACK}""".lstrip('\n')  # noqa


class DecoratorTests(unittest.TestCase):
    logs_dir = f'example/tests/{LOGS_DIR_NAME}'

    @classmethod
    @freezegun.freeze_time(FROZEN_TIME)
    def setUpClass(cls):
        for day in range(11, 11 + base.steps.max_history_length + 1):
            with open(os.path.join(cls.logs_dir, f'2019-03-{day}.log'), 'w') as log:
                log.write('This is a fake log')

        assert base.steps.scenarios == {
            'test_odd_boards': [], 'even_boards': [], 'test_start_board': []}

    @classmethod
    def tearDownClass(cls):
        assert len(os.listdir(cls.logs_dir)) <= base.steps.max_history_length

        shutil.rmtree(cls.logs_dir)

    def setUp(self):
        with open(os.path.join(base.steps.logs_dir, f'{FROZEN_TIME.date()}.log'), 'w'):
            pass

    @mock.patch(f'{NEW_GAME}.i_get_a_400_response_saying_it_must_be_even',
                return_value=None)
    @mock.patch(f'{NEW_GAME}.i_request_a_new_game_with_an_odd_number_of_boards',
                return_value=('Odd Game',))
    def assert_odd_boards(self, odd_mock, error_mock):
        tester = test_stories.ClearBoard()
        tester.test_odd_boards()

        odd_mock.assert_called_once_with()
        error_mock.assert_called_once_with()

        tester.tearDownClass()

    @mock.patch(f'{NEW_GAME}.i_get_a_400_response_saying_it_must_be_even',
                return_value=None)
    @mock.patch(f'{NEW_GAME}.i_request_a_new_game_with_an_odd_number_of_boards',
                return_value=('Odd Game',), side_effect=AssertionError('FAKE'))
    def assert_odd_boards__fail(self, odd_mock, error_mock):
        tester = test_stories.ClearBoard()
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
        tester = test_stories.ClearBoard()
        tester.test_start_board()

        even_mock.assert_called_once_with()
        created_mock.assert_called_once_with('12')
        clear_board_mock.assert_called_once_with()
        added_board_mock.assert_called_once_with()

        tester.tearDownClass()

    def assert_log(self, log_text):
        with open(os.path.join(base.steps.logs_dir, f'{FROZEN_TIME.date()}.log')) as log:
            assert log.read().startswith(log_text)

    @freezegun.freeze_time(FROZEN_TIME)
    def test_fail_traceback(self):
        with self.assertRaises(AssertionError) as cm:
            self.assert_odd_boards__fail()

        assert str(cm.exception).startswith(TRACEBACK)
        self.assert_log(FAIL_LOG)

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
