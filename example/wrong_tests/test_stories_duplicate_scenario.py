from . import base


class NewGame(base.BddTester):
    """
    As a codebreaker
    I want to start a new Mastermind game of B boards of G guesses
    In order to play
    """

    @base.BddTester.gherkin([9])
    def test_odd_boards(self):
        """
        When I request a new `game` with $n boards
        Then I get a 400 response saying it must be even
        And the number of boards is indeed odd
        """

    def i_request_a_new_game_with_n_boards(self, n):
        return 'game',

    def i_get_a_400_response_saying_it_must_be_even(self):
        assert False, 'Forced error'

    def the_number_of_boards_is_indeed_odd(self):
        assert False, 'Subsequent forced error'


class TestClearBoard(NewGame):
    """
    As a codebreaker
    I want a clear board with a new code
    In order to start making guesses on it
    """

    @base.BddTester.gherkin()
    def test_odd_boards(self):
        """
        Given I request a clear `board` in my new game
        """

    def i_request_a_clear_board_in_my_new_game(self):
        return 'board',
