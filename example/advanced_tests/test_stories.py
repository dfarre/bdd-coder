from . import base


def teardown_module():
    base.BddTester.gherkin.log(fail_if_pending=True)


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
        Then I get a 400 response saying it must be $(even)
        And pending scenario
        """

    @base.BddTester.gherkin([8, 'Boring', 9],
                            [6, 'Funny', 11])
    def even_boards(self):
        """
        When I request a new `game` with $n boards
        Then a game of $kind is created with boards of $guess_count guesses
        """

    @base.BddTester.gherkin([])
    def pending_scenario(self):
        """
        Then the number of boards is indeed odd
        """

    def i_request_a_new_game_with_n_boards(self, n):
        return 'game',

    async def i_get_a_400_response_saying_it_must_be(self):
        assert self.param == 'even'

        assert False, 'Forced error'

    def a_game_of_kind_is_created_with_boards_of_guess_count_guesses(self, kind, guess_count):
        pass

    def the_number_of_boards_is_indeed_odd(self):
        assert False, 'Subsequent forced error'


class TestClearBoard(NewGame):
    """
    As a codebreaker
    I want a clear board with a new code
    In order to start making guesses on it
    """

    @base.BddTester.gherkin(['Goat'], ['Cat'])
    def test_start_board(self):
        """
        Given even boards
        When I `request` a clear `board` in my new game
        Then the first board is added with the $animal
        """

    @base.BddTester.gherkin([0, 'Red'],
                            [1, 'Green'],
                            [2, 'Blue'])
    def test_start_colored_board(self):
        """
        Given even boards
        When I `request` a clear `board` in my new game
        Then the $nth board is added with the $color
        """

    def i_request_a_clear_board_in_my_new_game(self):
        return 'request-result', 'board-result'

    def the_first_board_is_added_with_the_animal(self, animal):
        print(animal)

    def the_nth_board_is_added_with_the_color(self, nth, n, color, pytestconfig):
        assert self.get_output('board') == 'board-result'
