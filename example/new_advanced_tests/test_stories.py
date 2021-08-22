from . import base


def teardown_module():
    base.gherkin.log()


class NewGame(base.BddTester):
    """
    As a codebreaker
    I want to start a new Mastermind game of B boards of G guesses
    In order to play
    """
    fixtures = ['player-alice']

    @base.gherkin.scenario([3, 'Kind', 7])
    def even_boards(self):
        """
        When I request a new `game` with $n boards
        Then a game of $kind is created with boards of $guess_count guesses
        """

    @base.gherkin.scenario([0])
    def test_odd_boards(self):
        """
        When I request a new `game` with $n boards
        Then I get a 400 response saying it must be even
        And the number of boards is indeed odd
        """

    def i_request_a_new_game_with_n_boards(self, n):
        return 'game',

    def a_game_of_kind_is_created_with_boards_of_guess_count_guesses(self, kind, guess_count):
        pass

    def i_get_a_400_response_saying_it_must_be_even(self):
        pass

    def the_number_of_boards_is_indeed_odd(self):
        pass


class Hiddenscenarios(NewGame):
    """
    The 'no end' scenario - ending with a scenario step - should show up in logs
    """

    @base.gherkin.scenario([True])
    def fine_scenario(self):
        """
        Given a first step with $param and $(input)
        When a second simple step
        Then the final third step
        """

    @base.gherkin.scenario()
    def no_end_scenario(self):
        """
        Given a new game
        Then fine scenario
        """

    @base.gherkin.scenario([3.14])
    def test_test_scenario(self):
        """
        Given no end scenario
        And the first test step with $new_param
        And a game of kind is created with boards of guess_count guesses
        And a first step with param and $(other input)
        Then final test step
        """

    def a_first_step_with_param_and(self, param, request):
        assert request.param.endswith('input')

    def a_second_simple_step(self):
        pass

    def the_final_third_step(self):
        assert True, 'What?'

    def the_first_test_step_with_new_param(self, new_param, guess_count):
        pass

    def final_test_step(self):
        pass


class TestClearBoard(Hiddenscenarios):
    """
    As a codebreaker
    I want a clear board with a new code
    In order to start making guesses on it
    """

    @base.gherkin.scenario(['Dog'])
    def test_start_board(self):
        """
        Given no end scenario
        When I `request` a clear `board` in my new game
        Then the first board is added with the $animal
        """

    @base.gherkin.scenario([8, 'Blue'])
    def test_start_colored_board(self):
        """
        Given no end scenario
        When I `request` a clear `board` in my new game
        Then the $nth board is added with the $color
        """

    def i_request_a_clear_board_in_my_new_game(self):
        return 'request', 'board'

    def the_first_board_is_added_with_the_animal(self, animal):
        pass

    def the_nth_board_is_added_with_the_color(self, nth, color):
        pass
