# BDD Coder
A package devoted to agile implementation of **class-based behavioural tests**. It consists of:

* [coder](https://bitbucket.org/coleopter/bdd-coder/src/master/bdd_coder/coder) package able to

    - make a tester package - test suite - blueprint - see [example/tests](https://bitbucket.org/coleopter/bdd-coder/src/master/example/tests) - from user story specifications in YAML files - see [example/specs](https://bitbucket.org/coleopter/bdd-coder/src/master/example/specs),

    - patch such tester package with new YAML specifications - see [example/new_specs](https://bitbucket.org/coleopter/bdd-coder/src/master/example/new_specs) and [example/new_tests](https://bitbucket.org/coleopter/bdd-coder/src/master/example/new_tests)

* [tester](https://bitbucket.org/coleopter/bdd-coder/src/master/bdd_coder/tester) package employed to run such blueprint tests, which also has the abiliry to export their docs as YAML specifications

Test with [tox](https://tox.readthedocs.io/en/latest/) - see tox.ini.

See [mastermind](https://bitbucket.org/coleopter/mastermind) for an application.

## Story
This package was born as a study of Behaviour Driven Development; and from the wish of having a handy implementation of Gherkin language in class-based tests, to be employed so that development cycles start with:

  1. A set of YAML specifications is agreed

  2. From these, a test suite is automatically created or patched

  3. New test methods are coded to efficiently achieve 100% behavioural coverage

## Tester
### Test run logging
Implemented behavioural test step runs are logged by `bdd_coder.tester` as
```
1 ✅ ClearBoard.even_boards:
  1.1 - 2019-03-18 17:30:13.071420 ✅ i_request_a_new_game_with_an_even_number_of_boards [] |--> ('Even Game',)
  1.2 - 2019-03-18 17:30:13.071420 ✅ a_game_is_created_with_boards_of__guesses ['12'] |--> ()

2 ✅ ClearBoard.test_start_board:
  2.1 - 2019-03-18 17:30:13.071420 ✅ even_boards [] |--> ()
  2.2 - 2019-03-18 17:30:13.071420 ✅ i_request_a_clear_board_in_my_new_game [] |--> ('Board',)
  2.3 - 2019-03-18 17:30:13.071420 ✅ board__is_added_to_the_game [] |--> ()

3 ❌ ClearBoard.test_odd_boards:
  3.1 - 2019-03-18 17:30:13.071420 ❌ i_request_a_new_game_with_an_odd_number_of_boards [] |--> Traceback (most recent call last):
  File "/usr/lib/python3.6/unittest/mock.py", line 939, in __call__
    return _mock_self._mock_call(*args, **kwargs)
  File "/usr/lib/python3.6/unittest/mock.py", line 995, in _mock_call
    raise effect
AssertionError: FAKE

Scenario runs {
    "1✅": "even_boards",
    "2✅": "test_start_board"
    "3❌": "test_odd_boards"
}
Pending []

All scenarios ran ▌ 2 ✅ ▌ 1 ❌
```
into `$logs_parent/.bdd-run-logs/` (git-ignored), split by date into files `YYYY-MM-DD.log`, with the `logs_parent` value passed to `bdd_coder.tester.decorators.Steps`, which also has a `max_history_length` parameter - in days, older history is removed.

In Ubuntu I use the bash function
```
function bdd-log-tab() {
  gnome-terminal --tab -- tail -f $(pwd)/$1/.bdd-run-logs/$(ls $(pwd)/$1/.bdd-run-logs | tail -1)
}
```
to open a terminal tab that will output the log stream as tests run (if the `.bdd-run-logs` directory exists).

### Commands
#### Check if pending scenarios
It may happen that all steps - and so all tests - that ran succeeded, but some scenarios were not reached. Run `bdd-pending-scenarios` after `pytest` to treat this as an error (recommended)
```
❌ Some scenarios did not run! Check the logs in [...]/.bdd-run-logs
```
```
usage: bdd-pending-scenarios [-h] logs_parent

positional arguments:
  logs_parent  Parent directory of .bdd-run-logs/
```

#### Export test suite docs as YAML
```
usage: bdd-make-yaml-specs [-h] [--overwrite] [--validate]
                           test_module specs_path

positional arguments:
  test_module      passed to importlib.import_module
  specs_path       will try to write the YAML files in here

optional arguments:
  -h, --help       show this help message and exit
  --overwrite, -w
  --validate, -v
```

## Coder commands
### Make a test suite blueprint
```
usage: bdd-blueprint [-h] [--base-class BASE_CLASS]
                     [--specs-path SPECS_PATH] [--tests-path TESTS_PATH]
                     [--test-module-name TEST_MODULE_NAME] [--overwrite]

optional arguments:
  --base-class BASE_CLASS, -c BASE_CLASS
                        default: unittest.TestCase
  --specs-path SPECS_PATH, -i SPECS_PATH
                        default: behaviour/specs
  --tests-path TESTS_PATH, -o TESTS_PATH
                        default: next to specs
  --test-module-name TEST_MODULE_NAME, -n TEST_MODULE_NAME
                        Name for test_<name>.py. default: stories
  --overwrite
```
The following:
```
bdd-coder$ bdd-blueprint -i example/specs -o example/tests --overwrite
```
will rewrite example/tests (with no changes if example/specs is unmodified), and run `pytest` on the blueprint yielding the output, like
```
============================= test session starts ==============================
platform [...]
collecting ... collected 2 items

example/tests/test_stories.py::ClearBoard::test_odd_boards PASSED        [ 50%]
example/tests/test_stories.py::ClearBoard::test_start_board PASSED       [100%]

=========================== 2 passed in 0.04 seconds ===========================
```

### Patch a test suite with new specifications
Use this command in order to update a tester package with new YAML specifications - removing scenario declarations only.
```
usage: bdd-patch [-h] test_module [specs_path]

positional arguments:
  test_module  passed to importlib.import_module
  specs_path   Directory to take new specs from. default: specs/ next to test package
```
The following:
```
bdd-coder$ bdd-patch example.tests.test_stories example/new_specs
```
will turn example/tests into example/new_tests, and run `pytest` on the suite yielding something like
```
============================= test session starts ==============================
platform [...]
collecting ... collected 3 items

example/tests/test_stories.py::NewGame::test_even_boards PASSED          [ 33%]
example/tests/test_stories.py::NewGame::test_funny_boards PASSED         [ 66%]
example/tests/test_stories.py::NewGame::test_more_boards PASSED          [100%]

=========================== 3 passed in 0.04 seconds ===========================
```
and a log
```
1 ✅ NewGame.new_player_joins:
  1.1 - 2019-04-01 00:30:50.164042 ✅ a_user_signs_in [] |--> ()
  1.2 - 2019-04-01 00:30:50.164059 ✅ a_new_player_is_added [] |--> ()

2 ✅ NewGame.test_even_boards:
  2.1 - 2019-04-01 00:30:50.164178 ✅ new_player_joins [] |--> ()
  2.2 - 2019-04-01 00:30:50.164188 ✅ i_request_a_new_game_with_an_even_number_of_boards [] |--> ('game',)
  2.3 - 2019-04-01 00:30:50.164193 ✅ a_game_is_created_with_boards_of__guesses ['12'] |--> ()

3 ✅ NewGame.new_player_joins:
  3.1 - 2019-04-01 00:30:50.165339 ✅ a_user_signs_in [] |--> ()
  3.2 - 2019-04-01 00:30:50.165348 ✅ a_new_player_is_added [] |--> ()

4 ✅ NewGame.test_funny_boards:
  4.1 - 2019-04-01 00:30:50.165422 ✅ new_player_joins [] |--> ()
  4.2 - 2019-04-01 00:30:50.165429 ✅ class_hierarchy_has_changed [] |--> ()

5 ✅ NewGame.new_player_joins:
  5.1 - 2019-04-01 00:30:50.166458 ✅ a_user_signs_in [] |--> ()
  5.2 - 2019-04-01 00:30:50.166466 ✅ a_new_player_is_added [] |--> ()

6 ✅ NewGame.test_more_boards:
  6.1 - 2019-04-01 00:30:50.166535 ✅ new_player_joins [] |--> ()
  6.2 - 2019-04-01 00:30:50.166541 ✅ user_is_welcome [] |--> ()

Scenario runs {
    "1✅-3✅-5✅": "new_player_joins",
    "2✅": "test_even_boards",
    "4✅": "test_funny_boards",
    "6✅": "test_more_boards"
}
Pending []

All scenarios ran ▌ 6 ✅
```
