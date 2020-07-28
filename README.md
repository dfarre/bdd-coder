# BDD Coder
[![PyPI version](https://badge.fury.io/py/bdd-coder.svg)](https://badge.fury.io/py/bdd-coder) [![PyPI downloads](https://img.shields.io/pypi/dm/bdd-coder.svg)](https://img.shields.io/pypi/dm/bdd-coder)

A package devoted to agile implementation of **class-based behavioral tests**. It consists of:

* [coder](https://bitbucket.org/coleopter/bdd-coder/src/master/bdd_coder/coder) package able to

    - make a tester package - test suite - blueprint - see [example/tests](https://bitbucket.org/coleopter/bdd-coder/src/master/example/tests) - from user story specifications in YAML files - see [example/specs](https://bitbucket.org/coleopter/bdd-coder/src/master/example/specs),

    - patch such tester package with new YAML specifications - see [example/new_specs](https://bitbucket.org/coleopter/bdd-coder/src/master/example/new_specs) and [example/new_tests](https://bitbucket.org/coleopter/bdd-coder/src/master/example/new_tests)

* [tester](https://bitbucket.org/coleopter/bdd-coder/src/master/bdd_coder/tester) package employed to run such blueprint tests, which also has the ability to export their docs as YAML specifications

Test with [tox](https://tox.readthedocs.io/en/latest/) - see tox.ini.

See [mastermind](https://bitbucket.org/coleopter/mastermind) for an application.

## Story
This package was born as a study of Behavior Driven Development; and from the wish of having a handy implementation of Gherkin language in class-based tests, to be employed so that development cycles start with coding a behavioral test suite containing the scenario specifications in test case method `__doc__`s - as `bdd_coder.tester` achieves.

In conjunction with `bdd_coder.coder`, development cycles *start* with:

1. A set of YAML specifications is agreed and crafted

2. From these, a test suite is automatically created or patched

3. New *test step methods* are crafted to efficiently achieve 100% behavioral coverage

## User Story (feature) specifications
Each test suite (tester package) has a structure
```
├─ __init__.py
├─ aliases.py
├─ base.py
└─ test_stories.py
```
corresponding to a specifications directory
```
├─ aliases.yml
└─ features/
   ├─ some-story.yml
   ├─ another-story.yml
   ├─ ...
   └─ this-story.yml
```
A story YAML file (the ones under features/) corresponds to a test case class declared into `test_stories.py`, consisting mainly of scenario declarations:
```
Title: <Story title>  # --> class __name__

Story: |-  # free text --> class __doc__
  As a <user group>
  I want <feature>
  In order to/so that <goal>

Scenarios:
  Scenario name:  # --> scenario __doc__
    - Step "1" with "A" gives `x` and `y`
      # ...
    - Last step with "B" gives `result`
  # ...

# Extra class atributes - ignored in patching
Extra name:
  <yaml-attribute-coded-with-str(yaml.load)>
...
```
So only the keys `Title`, `Story`, `Scenarios` are reserved.

Scenario names are unique if `bdd_coder.tester.decorators.Steps` takes `validate=True` (the default), which also validates class hierarchy.

### Step declarations
* Start with a whole word - normally 'Given', 'When', or 'Then' - that is ignored by the tester (only order matters)

* May contain:

    + Input `*args` sequence of values in double-quotes - passed to the step method

    + Output variable name sequence using backticks - if non-empty, the method should return the output values as a tuple, which are collected by the `bdd_coder.tester.decorators.Steps` decorator instance, by name into its `outputs` map of sequences

* May refer to a scenario name, either belonging to the same class (story), or to an inherited class

### Aliases
Declared as
```
Alias sentence:  # --> method to call
  - Step sentence  # from scenario __doc__s
  - Another step sentence
  # ...
# ...
```
corresponding to `aliases.py`:
```
MAP = {
    'step_sentence': 'alias_sentence',
    'another_step_sentence': 'alias_sentence',
    # ...
}
```

## Tester
The core of each test suite consists of the following required class declarations in its `base.py` module:
```
from test.case.module import MyTestCase

from bdd_coder.tester import decorators
from bdd_coder.tester import tester

from . import aliases

steps = decorators.Steps(aliases.MAP, logs_parent='example/tests')


@steps
class BddTester(tester.BddTester):
    """
    The decorated BddTester subclass of this suite - manages scenario runs
    """


class BaseTestCase(tester.BaseTestCase, MyTestCase):
    """
    The base test case of this suite - manages test runs
    """
```
Then, story test cases are declared in `test_stories.py`, with
```
from . import base
from bdd_coder.tester import decorators
```
as
```
class StoryTitle(BddTesterSubclass, AnotherBddTesterSubclass, ...[, base.BaseTestCase]):
```
with scenario declarations
```
  @decorators.Scenario(base.steps):
  def [test_]scenario_name(self):
      """
      Step "1" with "A" gives `x` and `y`
      ...
      Last step with "B" gives `result`
      """
```
that will run according to their `__doc__`s, and the necessary step method definitions.


### Test run logging
Implemented behavioural test step runs are logged by `bdd_coder.tester` as
```
1 ✅ ClearBoard.even_boards:
  1.1 - 2019-03-18 17:30:13.071420 ✅ i_request_a_new_game_with_an_even_number_of_boards [] ↦ ('Even Game',)
  1.2 - 2019-03-18 17:30:13.071420 ✅ a_game_is_created_with_boards_of__guesses ['12'] ↦ ()

2 ✅ ClearBoard.test_start_board:
  2.1 - 2019-03-18 17:30:13.071420 ✅ even_boards [] ↦ ()
  2.2 - 2019-03-18 17:30:13.071420 ✅ i_request_a_clear_board_in_my_new_game [] ↦ ('Board',)
  2.3 - 2019-03-18 17:30:13.071420 ✅ board__is_added_to_the_game [] ↦ ()

3 ❌ ClearBoard.test_odd_boards:
  3.1 - 2019-03-18 17:30:13.071420 ❌ i_request_a_new_game_with_an_odd_number_of_boards [] ↦ Traceback (most recent call last):
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
  --overwrite, -w
```
Additionally, validates code against generated specifications.

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
will rewrite [example/tests](https://bitbucket.org/coleopter/bdd-coder/src/master/example/tests) (with no changes if [example/specs](https://bitbucket.org/coleopter/bdd-coder/src/master/example/specs) is unmodified), and run `pytest` on the blueprint yielding the output, like
```
============================= test session starts ==============================
platform [...]
collecting ... collected 2 items

example/tests/test_stories.py::ClearBoard::test_odd_boards PASSED        [ 50%]
example/tests/test_stories.py::ClearBoard::test_start_board PASSED       [100%]

=========================== 2 passed in 0.04 seconds ===========================
```

### Patch a test suite with new specifications
Use this command in order to update a tester package with new YAML specifications - removes scenario declarations *only*, changes the scenario set, which may imply a new test class hierarchy with new stories and scenarios, adds the necessary step methods, and adds new aliases (if any).
```
usage: bdd-patch [-h] test_module [specs_path]

positional arguments:
  test_module  passed to importlib.import_module
  specs_path   Directory to take new specs from. default: specs/ next to test package

optional arguments:
  --scenario-delimiter SCENARIO_DELIMITER, -d SCENARIO_DELIMITER
                        default: @decorators.Scenario(base.steps)
```
The following:
```
bdd-coder$ bdd-patch example.tests.test_stories example/new_specs
```
will turn [example/tests](https://bitbucket.org/coleopter/bdd-coder/src/master/example/tests) into [example/new_tests](https://bitbucket.org/coleopter/bdd-coder/src/master/example/new_tests), and run `pytest` on the suite yielding something like
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
  1.1 - 2019-04-01 00:30:50.164042 ✅ a_user_signs_in [] ↦ ()
  1.2 - 2019-04-01 00:30:50.164059 ✅ a_new_player_is_added [] ↦ ()

2 ✅ NewGame.test_even_boards:
  2.1 - 2019-04-01 00:30:50.164178 ✅ new_player_joins [] ↦ ()
  2.2 - 2019-04-01 00:30:50.164188 ✅ i_request_a_new_game_with_an_even_number_of_boards [] ↦ ('game',)
  2.3 - 2019-04-01 00:30:50.164193 ✅ a_game_is_created_with_boards_of__guesses ['12'] ↦ ()

3 ✅ NewGame.new_player_joins:
  3.1 - 2019-04-01 00:30:50.165339 ✅ a_user_signs_in [] ↦ ()
  3.2 - 2019-04-01 00:30:50.165348 ✅ a_new_player_is_added [] ↦ ()

4 ✅ NewGame.test_funny_boards:
  4.1 - 2019-04-01 00:30:50.165422 ✅ new_player_joins [] ↦ ()
  4.2 - 2019-04-01 00:30:50.165429 ✅ class_hierarchy_has_changed [] ↦ ()

5 ✅ NewGame.new_player_joins:
  5.1 - 2019-04-01 00:30:50.166458 ✅ a_user_signs_in [] ↦ ()
  5.2 - 2019-04-01 00:30:50.166466 ✅ a_new_player_is_added [] ↦ ()

6 ✅ NewGame.test_more_boards:
  6.1 - 2019-04-01 00:30:50.166535 ✅ new_player_joins [] ↦ ()
  6.2 - 2019-04-01 00:30:50.166541 ✅ user_is_welcome [] ↦ ()

Scenario runs {
    "1✅-3✅-5✅": "new_player_joins",
    "2✅": "test_even_boards",
    "4✅": "test_funny_boards",
    "6✅": "test_more_boards"
}
Pending []

All scenarios ran ▌ 6 ✅
```
