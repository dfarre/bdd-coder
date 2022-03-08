# BDD Coder
[![PyPI version](https://badge.fury.io/py/bdd-coder.svg)](https://badge.fury.io/py/bdd-coder) [![PyPI downloads](https://img.shields.io/pypi/dm/bdd-coder.svg)](https://img.shields.io/pypi/dm/bdd-coder)

A package devoted to agile implementation of **class-based behavior tests**. It consists of (see [example](https://bitbucket.org/coleopter/bdd-coder/src/master/example/)):
* [coders](https://bitbucket.org/coleopter/bdd-coder/src/master/bdd_coder/coders.py) module able to
    - make a tester package - test suite - blueprint from user story specifications in YAML files
    - patch such tester package with new YAML specifications
* [tester](https://bitbucket.org/coleopter/bdd-coder/src/master/bdd_coder/tester.py) module employed to run such blueprint tests, which also has the ability to export their docs as YAML specifications

Although this package is intended to be used with [pytest](https://docs.pytest.org/en/stable/contents.html), until version 2.0.0 the base test case class for all test suits `bdd_coder.tester.tester.BaseTestCase` was a `unittest.TestCase` subclass. From version 2.0.0 `unittest.TestCase` is no longer supported, so that `pytest`'s setup and teardown functions - see [pytest-xunit_setup](https://docs.pytest.org/en/latest/xunit_setup.html) - should be implemented instead. See [pytest-unittest](https://docs.pytest.org/en/stable/unittest.html#pytest-features-in-unittest-testcase-subclasses) on the benefits of dropping `unittest.TestCase`.

See [mastermind](https://bitbucket.org/coleopter/mastermind) for an example testing a Django REST Framework API.

Test this package with [tox](https://tox.readthedocs.io/en/latest/) - see tox.ini.

## Story
This package was born as a study of Behavior Driven Development; and from the wish of having a handy implementation of Gherkin language in class-based tests, to be employed so that development cycles start with coding a behavior test suite containing the scenario specifications in test case method `__doc__`s - as `bdd_coder.tester` achieves.

In conjunction with `bdd_coder.coder`, development cycles *start* with:
1. A set of YAML specifications is agreed and crafted
2. From these, a test suite is automatically created or patched
3. New *test step methods* are crafted to efficiently achieve 100% behavior coverage

## User Story (feature) specifications
Each test suite (tester package) has a structure
```
├─ __init__.py
├─ base.py
└─ test_stories.py
```
corresponding to a specifications directory with story YAML files
```
├─ some-story.yml
├─ another-story.yml
├─ ...
└─ this-story.yml
```
A story file corresponds to a test case class declared into `test_stories.py`, consisting mainly of scenario declarations:
```
Title: <Story title>  # --> class __name__

Story: |-  # free text --> class __doc__
  As a <user group>
  I want <feature>
  In order to/so that <goal>

Scenarios:
  Scenario name:  # --> scenario __doc__
    - Given an event $(1) with $(A) and $first_param that gives `x` and `y`
    - When it happens that...
    - And the parameters $second and $third enter
    - Then finally we assert that...
    # ...
  # ...
```
Only the keys `Title`, `Story`, `Scenarios` are required and mean something.

### Step declarations
A scenario declaration consists of a list of step declarations, which:
* Correspond to a test step method to be defined
* Start with a whole word - normally 'Given', 'When', or 'Then' - that is ignored by the tester (only order matters)
* May contain:
    + Input string values as $(...), which are passed as Pytest fixture parameters to the step method, so that they are available from the Pytest `request` fixture as the tuple `request.param`
    + Input parameter names as $param_name, which are passed to Pytest's parametrize
    + Output variable name sequence using backticks - if non-empty, the method should return the output values as a tuple, which are collected by the `bdd_coder.tester.decorators.Gherkin` decorator instance, by name into its `outputs` map of sequences
* May refer to a scenario name, either belonging to the same class (story), or to an inherited class

## Tester
The core of each test suite consists of the following required class declaration in its `base.py` module:
```python
from bdd_coder import decorators
from bdd_coder import tester

gherkin = decorators.Gherkin(logs_path='example/tests/bdd_runs.log')


@gherkin
class BddTester(tester.BddTester):
    """
    The decorated BddTester subclass of this tester package.
    It manages scenario runs. All test classes inherit from this one,
    so generic test methods for this package are expected to be defined here
    """
```
Then, story test cases are declared in `test_stories.py`, with the `base` module imported, scenario declarations such as
```python
class StoryTitle(BddTesterSubclass, AnotherBddTesterSubclass):
    @base.gherkin.scenario(['param1_value1'], ['param1_value2'])
    def test_scenario_name(self):
        """
        Given $(input1) and $param1 step one gives `x` and `y`
        ...
        Last step with $(input2) gives `result`
        """
```
that will run according to their `__doc__`s, and the necessary step method definitions.

### Commands
#### Export test suite docs as YAML
```
usage: bdd-make-yaml-specs [-h] [--overwrite] test_module specs_path

positional arguments:
  test_module      str. Passed to `importlib.import_module`
  specs_path       str. Will try to write the YAML files in here

keyword arguments:
  --overwrite, -o
```
Additionally, validates code against generated specifications.

## Coder commands
### Make a test suite blueprint
```
usage: bdd-blueprint [-h] [--base-class BASE_CLASS]
                     [--specs-path SPECS_PATH] [--tests-path TESTS_PATH]
                     [--test-module-name TEST_MODULE_NAME] [--overwrite]

keyword arguments:
  --base-class BASE_CLASS, -b BASE_CLASS
                        str. Base test case class
  --specs-path SPECS_PATH, -s SPECS_PATH
                        str. Default: behaviour/specs. Directory containing the YAML specs
  --tests-path TESTS_PATH, -t TESTS_PATH
                        str. Default: next to specs
  --test-module-name TEST_MODULE_NAME, -tm TEST_MODULE_NAME
                        str. Default: stories. Name for test_<name>.py
  --overwrite, -o
```
The following:
```
bdd-coder$ bdd-blueprint -s example/specs -t example/tests --overwrite
```
will rewrite [example/tests](https://bitbucket.org/coleopter/bdd-coder/src/master/example/tests) (with no changes if [example/specs](https://bitbucket.org/coleopter/bdd-coder/src/master/example/specs) is unmodified), and run `pytest` on the blueprint yielding the output, like
```
============================= test session starts ==============================
platform [...]
collecting ... collected 2 items

example/tests/test_stories.py::TestClearBoard::test_odd_boards PASSED    [ 50%]
example/tests/test_stories.py::TestClearBoard::test_start_board PASSED   [100%]

=========================== 2 passed in 0.04 seconds ===========================
```

### Patch a test suite with new specifications
Use this command in order to update a tester package with new YAML specifications. It removes scenario declarations *only*; it changes the scenario set, which may imply a new test class hierarchy with new stories and scenarios; it adds the necessary step methods, and new aliases (if any).
```
usage: bdd-patch [-h] test_module [specs_path]

positional arguments:
  test_module  str. Passed to `importlib.import_module`
  specs_path   str. Directory to take new specs from. Default: specs/ next to test package
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

example/tests/test_stories.py::TestNewGame::test_even_boards PASSED      [ 33%]
example/tests/test_stories.py::TestNewGame::test_funny_boards PASSED     [ 66%]
example/tests/test_stories.py::TestNewGame::test_more_boards PASSED      [100%]

=========================== 3 passed in 0.04 seconds ===========================
```
