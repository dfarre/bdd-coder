# BDD Coder

A package devoted to agile implementation of class-based behavioural tests.
It consists of:

1. A `tester` package with `decorators` module to be employed as shown in tests/test_decorators.py
2. A `coders` package that allows to make a tester package blueprint from user story
   specifications in YAML files - see tests/example_specs. Then you just implement
   the methods defined and the test suite is done - that's the idea.

See [mastermind](https://bitbucket.org/coleopter/mastermind) for an application.
