import unittest
import unittest.mock as mock

from bdd_coder.tester import decorators
from bdd_coder.tester import tester


@decorators.Steps({'a_game_is_created_with_boards_of__guesses': 'post_game'})
class NewGame(tester.BddTestCase):
    """
    As a codebreaker
    I want to start a new Mastermind game of B boards of G guesses
    In order to play
    """

    @decorators.scenario
    def A_odd_boards(self):
        """
        When I request a new `game` with an odd number of boards
        Then I get a 400 response saying it must be even
        """

    @decorators.scenario
    def B_even_boards(self):
        """
        When I request a new `game` with an even number of boards
        Then a game is created with boards of "12" guesses
        """

    def i_request_a_new_game_with_an_even_number_of_boards(self, *args, **kwargs):
        return 'Even Game',

    def i_request_a_new_game_with_an_odd_number_of_boards(self, *args, **kwargs):
        return 'Odd Game',

    def i_get_a_400_response_saying_it_must_be_even(self, *args, **kwargs):
        pass

    def post_game(self, *args, **kwargs):
        pass

    def _test(self):
        self.A_odd_boards()
        self.B_even_boards()


PATH = f'{NewGame.__module__}.NewGame'


class DecoratorTests(unittest.TestCase):
    new_game_tester = NewGame()

    @mock.patch(f'{PATH}.i_get_a_400_response_saying_it_must_be_even')
    @mock.patch(f'{PATH}.i_request_a_new_game_with_an_odd_number_of_boards',
                return_value=('Odd Game',))
    @mock.patch(f'{PATH}.post_game')
    @mock.patch(f'{PATH}.i_request_a_new_game_with_an_even_number_of_boards',
                return_value=('Even Game',))
    def test_steps_mapping__args_and_kwargs_passed(
            self, even_mock, post_game_mock, odd_mock, error_mock):
        self.new_game_tester._test()

        odd_mock.assert_called_once_with()
        error_mock.assert_called_once_with(game=['Odd Game', 'Even Game'])
        even_mock.assert_called_once_with(game=['Odd Game', 'Even Game'])
        post_game_mock.assert_called_once_with('12', game=['Odd Game', 'Even Game'])
