from . import base


class NewGame(base.BddTester):
    """
    As a codebreaker
    I want to start a new Mastermind game of B boards of G guesses
    In order to play
    """
    fixtures = ['player-alice']

    @base.gherkin.scenario([9])
    def test_odd_boards(self):
        """
        When I request a new `game` with $n boards
        Then I get a 400 response saying it must be even
        And the number $n of boards is indeed odd
        """

    @base.gherkin.scenario([8, 'Boring', 9], [6, 'Funny', 11])
    def even_boards(self):  # n,kind,guess_count param values
        """
        When I request a new `game` with $n boards
        Then a game of $kind is created with boards of $guess_count guesses
        """

    def i_request_a_new_game_with_n_boards(self, n):
        return 'game',

    def i_get_a_400_response_saying_it_must_be_even(self):
        assert False, 'Forced error'

    def a_game_of_kind_is_created_with_boards_of_guess_count_guesses(self, kind, guess_count):
        pass

    def the_number_n_of_boards_is_indeed_odd(self):
        assert False, 'Subsequent forced error'


class TestClearBoard(NewGame):
    """
    As a codebreaker
    I want a clear board with a new code
    In order to start making guesses on it
    """

    @base.gherkin.scenario([0, 'Goat'], [1, 'Cat'])
    def test_start_board(self):  # additional animal param
        """
        Given a new game
        When I request a clear `board` in my new $n game
        Then the first board is added with the $animal
        """

    @base.gherkin.scenario([0, 'Red'], [1, 'Green'], [2, 'Blue'])
    def test_start_colored_board(self):  # additional nth,color params
        """
        Given a new game
        When I request a clear `board` in my new $n game
        Then the $nth board is added with the $color
        """

    def i_request_a_clear_board_in_my_new_n_game(self):
        return 'board',

    def the_first_board_is_added_with_the_animal(self, animal):
        pass

    def the_nth_board_is_added_with_the_color(self, nth, n, color, pytestconfig):
        assert self.get_output('board') == 'board'
