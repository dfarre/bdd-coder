import unittest
import unittest.mock as mock

from example.tests import base
from example.tests import test_stories

NEW_GAME = 'example.tests.test_stories.NewGame'
CLEAR_BOARD = 'example.tests.test_stories.ClearBoard'


class DecoratorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        assert base.steps.scenarios == {
            'test_odd_boards': [], 'even_boards': [], 'test_start_board': []}

        super().setUpClass()

    @mock.patch(f'{NEW_GAME}.i_get_a_400_response_saying_it_must_be_even')
    @mock.patch(f'{NEW_GAME}.i_request_a_new_game_with_an_odd_number_of_boards',
                return_value=('Odd Game',))
    def test_odd_boards(self, odd_mock, error_mock):
        test_stories.NewGame().test_odd_boards()

        odd_mock.assert_called_once_with()
        assert base.steps.outputs['game'][-1] == 'Odd Game'
        error_mock.assert_called_once_with()

    @mock.patch(f'{CLEAR_BOARD}.board__is_added_to_the_game')
    @mock.patch(f'{CLEAR_BOARD}.i_request_a_clear_board_in_my_new_game',
                return_value=('Board',))
    @mock.patch(f'{NEW_GAME}.a_game_is_created_with_boards_of__guesses')
    @mock.patch(f'{NEW_GAME}.i_request_a_new_game_with_an_even_number_of_boards',
                return_value=('Even Game',))
    def test_start_board(self, even_mock, created_mock, clear_board_mock, added_board_mock):
        test_stories.ClearBoard().test_start_board()

        even_mock.assert_called_once_with()
        assert base.steps.outputs['game'][-1] == 'Even Game'
        created_mock.assert_called_once_with('12')
        clear_board_mock.assert_called_once_with()
        assert base.steps.outputs['board'][-1] == 'Board'
        clear_board_mock.assert_called_once_with()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()

        assert list(map(len, base.steps.scenarios.values())) == [1]*len(base.steps.scenarios)
        assert (base.steps.scenarios['test_start_board'][0]
                == base.steps.scenarios['even_boards'][0] + 1)
