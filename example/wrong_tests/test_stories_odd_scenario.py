from . import base


class NewGame(base.BddTester):
    """
    As a codebreaker
    I want to start a new Mastermind game of B boards of G guesses
    In order to play
    """
    fixtures = ['player-alice']

    @base.gherkin.scenario()
    def test_odd_boards(self):
        """
        When I request a new `game` with an odd number of boards
        Then I get a 400 response saying it must be even
        """

    @base.gherkin.scenario()
    def even_boards(self, *args):
        """
        When I request a new `game` with an even number of boards
        Then a game is created with boards of $guess_count guesses
        """

    def i_request_a_new_game_with_an_odd_number_of_boards(self):
        return 'game',

    def i_get_a_400_response_saying_it_must_be_even(self):
        pass

    def i_request_a_new_game_with_an_even_number_of_boards(self):
        return 'game',

    def a_game_is_created_with_boards_of_guess_count_guesses(self, guess_count):
        pass


class TestClearBoard(NewGame):
    """
    As a codebreaker
    I want a clear board with a new code
    In order to start making guesses on it
    """

    @base.gherkin.scenario()
    def test_start_board(self):
        """
        Given a new game
        When I request a clear `board` in my new game
        Then the first board is added to the game
        """

    def i_request_a_clear_board_in_my_new_game(self):
        return 'board',
