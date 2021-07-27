from . import base


class ClearBoard(base.BddTester):
    """
    As a codebreaker
    I want a clear board with a new code
    In order to start making guesses on it
    """

    def i_request_a_clear_board_in_my_new_game(self):
        return 'board',


class NewPlayer(base.BddTester):
    """
    As a user
    I want to sign in
    In order to play
    """

    @base.gherkin.scenario()
    def new_player_joins(self):
        """
        When a user signs in
        Then a new player is added
        """

    def a_user_signs_in(self):
        pass

    def a_new_player_is_added(self):
        pass


class TestNewGame(NewPlayer):
    """
    As a codebreaker
    I want to start a new Mastermind game of B boards of G guesses
    In order to play and have fun
    """
    fixtures = ['player-alice']

    @base.gherkin.scenario()
    def test_even_boards(self):
        """
        Given new player joins
        When I request a new `game` with an even number of boards
        Then a game is created with boards of $guess_count guesses
        """

    @base.gherkin.scenario()
    def test_funny_boards(self):
        """
        Given new player joins
        Then class hierarchy has changed
        """

    @base.gherkin.scenario()
    def test_more_boards(self):
        """
        Given new player joins
        Then she is welcome
        """

    def i_request_a_new_game_with_boards(self):
        return 'game',

    def i_get_a_400_response_saying_it_must_be_even(self):
        pass

    def a_game_is_created_with_boards_of_guess_count_guesses(self, guess_count):
        pass

    def i_request_a_new_game_with_an_even_number_of_boards(self):
        return 'game',

    def class_hierarchy_has_changed(self):
        pass
