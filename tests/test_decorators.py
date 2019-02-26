import datetime
import os
import shutil
import unittest
import unittest.mock as mock

import freezegun

NEW_GAME = 'example.tests.test_stories.NewGame'
CLEAR_BOARD = 'example.tests.test_stories.ClearBoard'

FROZEN_TIME = datetime.datetime(2019, 2, 26, 17, 30, 13, 71420)
FIRST_LOG = f"""
_________________________________________
{FROZEN_TIME} Steps prepared

1 ✓ ClearBoard.even_boards:
  1.1 - {FROZEN_TIME} ✓ i_request_a_new_game_with_an_even_number_of_boards [] |--> ('Even Game',)
  1.2 - {FROZEN_TIME} ✓ a_game_is_created_with_boards_of__guesses ['12'] |--> ()

2 ✓ ClearBoard.test_start_board:
  2.1 - {FROZEN_TIME} ✓ even_boards [] |--> ()
  2.2 - {FROZEN_TIME} ✓ i_request_a_clear_board_in_my_new_game [] |--> ('Board',)
  2.3 - {FROZEN_TIME} ✓ board__is_added_to_the_game [] |--> ()

ClearBoard - Scenario runs {{
    "1": "even_boards",
    "2": "test_start_board"
}}
Pending [
    "test_odd_boards"
]

""".lstrip('\n')
SECOND_LOG = f"""
3 ✓ ClearBoard.test_odd_boards:
  3.1 - {FROZEN_TIME} ✓ i_request_a_new_game_with_an_odd_number_of_boards [] |--> ('Odd Game',)
  3.2 - {FROZEN_TIME} ✓ i_get_a_400_response_saying_it_must_be_even [] |--> ()

ClearBoard - Scenario runs {{
    "1": "even_boards",
    "2": "test_start_board",
    "3": "test_odd_boards"
}}
Pending []

▌ All scenarios ran successfully! ✅

""".lstrip('\n')


class DecoratorTests(unittest.TestCase):
    @classmethod
    @freezegun.freeze_time(FROZEN_TIME)
    def setUpClass(cls):
        shutil.rmtree('example/tests/.bdd-run-logs')
        from example.tests import base
        from example.tests import test_stories

        assert base.steps.scenarios == {
            'test_odd_boards': [], 'even_boards': [], 'test_start_board': []}

        cls.test_stories = test_stories
        cls.steps = base.steps

        super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()

        assert list(map(len, cls.steps.scenarios.values())) == [1]*len(cls.steps.scenarios)
        assert cls.steps.scenarios == {
            'test_odd_boards': [3], 'even_boards': [1], 'test_start_board': [2]}

    @mock.patch(f'{NEW_GAME}.i_get_a_400_response_saying_it_must_be_even',
                return_value=None)
    @mock.patch(f'{NEW_GAME}.i_request_a_new_game_with_an_odd_number_of_boards',
                return_value=('Odd Game',))
    def assert_odd_boards(self, odd_mock, error_mock):
        tester = self.test_stories.ClearBoard()
        tester.test_odd_boards()

        odd_mock.assert_called_once_with()
        error_mock.assert_called_once_with()

        tester.tearDownClass()

    @mock.patch(f'{CLEAR_BOARD}.board__is_added_to_the_game',
                return_value=None)
    @mock.patch(f'{CLEAR_BOARD}.i_request_a_clear_board_in_my_new_game',
                return_value=('Board',))
    @mock.patch(f'{NEW_GAME}.a_game_is_created_with_boards_of__guesses',
                return_value=None)
    @mock.patch(f'{NEW_GAME}.i_request_a_new_game_with_an_even_number_of_boards',
                return_value=('Even Game',))
    def assert_start_board(self, even_mock, created_mock, clear_board_mock, added_board_mock):
        tester = self.test_stories.ClearBoard()
        tester.test_start_board()

        even_mock.assert_called_once_with()
        created_mock.assert_called_once_with('12')
        clear_board_mock.assert_called_once_with()
        added_board_mock.assert_called_once_with()

        tester.tearDownClass()

    def assert_log(self, log_text):
        with open(os.path.join(self.steps.logs_dir, f'{FROZEN_TIME.date()}.log')) as log:
            assert log.read() == log_text

    @freezegun.freeze_time(FROZEN_TIME)
    def test(self):
        self.assert_start_board()
        assert self.steps.outputs['game'] == ['Even Game']
        assert self.steps.outputs['board'] == ['Board']
        self.assert_log(FIRST_LOG)
        self.assert_odd_boards()
        assert self.steps.outputs['game'] == ['Even Game', 'Odd Game']
        self.assert_log(FIRST_LOG + SECOND_LOG)
