# BDD Coder

A package devoted to agile implementation of class-based behavioural tests.
It consists of:

1. A `coders` package that allows to make a tester package blueprint - see
   example/tests - from user story specifications in YAML files - see example/specs
2. The `tester` package employed in the blueprint. This can be employed
   independently to make a behavioural test suite, and YAML specifications may
   be extracted from test modules

Test with [tox](https://tox.readthedocs.io/en/latest/) - see tox.ini.

See [mastermind](https://bitbucket.org/coleopter/mastermind) for an application.
