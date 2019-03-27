from bdd_coder.tester import decorators

from . import base


class ClearBoard(base.BddTester):
    """
    As a codebreaker
    I want a clear board with a new code
    In order to start making guesses on it
    """


class NewPlayer(base.BddTester):
    """
    As a user
    I want to sign in
    In order to play
    """

    @decorators.Scenario(base.steps)
    def new_player_joins(self):
        """
        When a user signs in
        Then a new player is added
        """

    def a_user_signs_in(self, *args):
        assert len(args) == 0

    def a_new_player_is_added(self, *args):
        assert len(args) == 0


class NewGame(NewPlayer, base.BaseTestCase):
    """
    As a codebreaker
    I want to start a new Mastermind game of B boards of G guesses
    In order to play
    """
    fixtures = ['player-alice']

    @decorators.Scenario(base.steps)
    def test_funny_boards(self):
        """
        Given new player joins
        Then class hierarchy has changed
        """

    @decorators.Scenario(base.steps)
    def test_more_boards(self):
        """
        Given new player joins
        Then she is welcome
        """

    @decorators.Scenario(base.steps)
    def test_even_boards(self):
        """
        Given new player joins
        When I request a new `game` with an even number of boards
        Then a game is created with boards of "12" guesses
        """

    def i_request_a_new_game_with_an_odd_number_of_boards(self, *args):
        assert len(args) == 0

        return 'game',

    def i_get_a_400_response_saying_it_must_be_even(self, *args):
        assert len(args) == 0

    def i_request_a_new_game_with_an_even_number_of_boards(self, *args):
        assert len(args) == 0

        return 'game',

    def a_game_is_created_with_boards_of__guesses(self, *args):
        assert len(args) == 1

    def class_hierarchy_has_changed(self, *args):
        assert len(args) == 0
