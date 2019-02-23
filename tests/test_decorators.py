import unittest
import unittest.mock as mock

from bdd_coder.tester import decorators
from bdd_coder.tester import tester

steps = decorators.Steps({
    'a_new_game': 'even_boards',
    'the_first_board_is_added_to_the_game': 'board__is_added_to_the_game'}, 'tests')


@steps
class NewGame(tester.BddTester):
    """
    As a codebreaker
    I want to start a new Mastermind game of B boards of G guesses
    In order to play
    """

    @decorators.Scenario(steps)
    def _test_odd_boards(self):
        """
        When I request a new `game` with an odd number of boards
        Then I get a 400 response saying it must be even
        """

    @decorators.Scenario(steps)
    def even_boards(self):
        """
        When I request a new `game` with an even number of boards
        Then a game is created with boards of "12" guesses
        """

    def i_request_a_new_game_with_an_odd_number_of_boards(self, *args):
        assert len(args) == 0

        return 'Odd Game',

    def i_get_a_400_response_saying_it_must_be_even(self, *args):
        assert len(args) == 0

    def i_request_a_new_game_with_an_even_number_of_boards(self, *args):
        assert len(args) == 0

        return 'Even Game',

    def a_game_is_created_with_boards_of__guesses(self, *args):
        assert len(args) == 1


class ClearBoard(NewGame, tester.BaseTestCase):
    """
    As a codebreaker
    I want a clear board with a new code
    In order to start making guesses on it
    """

    @decorators.Scenario(steps)
    def _test_start_board(self):
        """
        Given a new game
        When I request a clear `board` in my new game
        Then the first board is added to the game
        """

    def i_request_a_clear_board_in_my_new_game(self, *args):
        assert len(args) == 0

        return 'Board',

    def board__is_added_to_the_game(self, *args):
        assert len(args) == 0


NEW_GAME = f'{NewGame.__module__}.NewGame'
CLEAR_BOARD = f'{ClearBoard.__module__}.ClearBoard'


class DecoratorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        assert steps.scenarios == {
            '_test_odd_boards': [], 'even_boards': [], '_test_start_board': []}

        super().setUpClass()

    @mock.patch(f'{NEW_GAME}.i_get_a_400_response_saying_it_must_be_even')
    @mock.patch(f'{NEW_GAME}.i_request_a_new_game_with_an_odd_number_of_boards',
                return_value=('Odd Game',))
    def test_odd_boards(self, odd_mock, error_mock):
        NewGame()._test_odd_boards()

        odd_mock.assert_called_once_with()
        assert steps.outputs['game'][-1] == 'Odd Game'
        error_mock.assert_called_once_with()

    @mock.patch(f'{CLEAR_BOARD}.board__is_added_to_the_game')
    @mock.patch(f'{CLEAR_BOARD}.i_request_a_clear_board_in_my_new_game',
                return_value=('Board',))
    @mock.patch(f'{NEW_GAME}.a_game_is_created_with_boards_of__guesses')
    @mock.patch(f'{NEW_GAME}.i_request_a_new_game_with_an_even_number_of_boards',
                return_value=('Even Game',))
    def test_start_board(self, even_mock, created_mock, clear_board_mock, added_board_mock):
        ClearBoard()._test_start_board()

        even_mock.assert_called_once_with()
        assert steps.outputs['game'][-1] == 'Even Game'
        created_mock.assert_called_once_with('12')
        clear_board_mock.assert_called_once_with()
        assert steps.outputs['board'][-1] == 'Board'
        clear_board_mock.assert_called_once_with()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()

        assert list(map(len, steps.scenarios.values())) == [1]*len(steps.scenarios)
        assert (steps.scenarios['_test_start_board'][0]
                == steps.scenarios['even_boards'][0] + 1)
