import abc
import collections
import datetime
import inspect
import os
import re
import shutil
import sys
import yaml

from bdd_coder import extract_name
from bdd_coder import strip_lines
from bdd_coder import to_sentence
from bdd_coder import FAIL, OK, TO, COMPLETION_MSG
from bdd_coder import Step

from bdd_coder import exceptions
from bdd_coder import features
from bdd_coder import stock

from bdd_coder.exceptions import InconsistentClassStructure


class literal(str):
    """Employed to make nice YAML files"""


class YamlDumper:
    @staticmethod
    def dump_yaml(data, path):
        yaml.add_representer(collections.OrderedDict,
                             lambda dumper, data: dumper.represent_dict(data.items()))
        yaml.add_representer(literal, lambda dumper, data: dumper.represent_scalar(
            'tag:yaml.org,2002:str', data, style='|'))

        with open(path, 'w') as yml_file:
            yaml.dump(data, yml_file, default_flow_style=False)

    @classmethod
    def dump_yaml_aliases(cls, aliases, parent_dir):
        alias_lists = collections.defaultdict(list)

        for item in aliases.items():
            name, alias = map(to_sentence, item)
            alias_lists[alias].append(name)

        cls.dump_yaml(dict(alias_lists), os.path.join(parent_dir, 'aliases.yml'))


class BddTesterABC(YamlDumper, stock.SubclassesMixin, metaclass=abc.ABCMeta):
    """
    To be decorated with `Steps`, and employed with methods decorated with
    `scenario` - mixes with a subclass of `BaseTestCase` to run test methods
    """
    tmp_dir = '.tmp-specs'

    @classmethod
    def validate(cls):
        cls.validate_bases(cls.features_spec())

    @classmethod
    def features_spec(cls, parent_dir=None, overwrite=True):
        directory = parent_dir or cls.tmp_dir
        cls.dump_yaml_specs(directory, overwrite)

        try:
            return features.FeaturesSpec.from_specs_dir(directory)
        except exceptions.FeaturesSpecError as error:
            raise error
        finally:
            if parent_dir is None:
                shutil.rmtree(directory)

    @classmethod
    def validate_bases(cls, features_spec):
        spec_bases = collections.OrderedDict(features_spec.class_bases)
        cls_bases = collections.OrderedDict(
            (extract_name(c.__name__), b) for c, b in cls.subclasses_down().items())
        pair = stock.SetPair(spec_bases, cls_bases, lname='doc', rname='code')
        errors = []

        if not pair.symbol == '=':
            raise InconsistentClassStructure(error=f'Sets of class names differ: {repr(pair)}')

        for name in spec_bases:
            own_bases = set(cls_bases[name])
            own_bases.discard(cls)
            base_test_cases = [b for b in own_bases if issubclass(b, BaseTestCase)]

            if features_spec.features[name]['inherited'] and len(base_test_cases) != 0:
                errors.append(f'unexpected {BaseTestCase.__name__} subclass in {name}')

            if not features_spec.features[name]['inherited'] and len(base_test_cases) != 1:
                errors.append(f'expected one {BaseTestCase.__name__} subclass in {name}')

            own_bases_names = {b.__name__ for b in own_bases if b not in base_test_cases}

            if own_bases_names != spec_bases[name]:
                errors.append(f'bases {own_bases_names} declared in {name} do not '
                              f'match the specified ones {spec_bases[name]}')

        if errors:
            raise InconsistentClassStructure(error=', '.join(errors))

        sys.stdout.write('Test case hierarchy validated\n')

    @classmethod
    def dump_yaml_specs(cls, parent_dir, overwrite=False):
        exceptions.makedirs(parent_dir, exist_ok=overwrite)
        features_path = os.path.join(parent_dir, 'features')
        exceptions.makedirs(features_path, exist_ok=overwrite)

        cls.dump_yaml_aliases(cls.steps.aliases, parent_dir)

        for tester_subclass in cls.subclasses_down():
            tester_subclass.dump_yaml_feature(features_path)

        sys.stdout.write(f'Specification files generated in {parent_dir}\n')

    @classmethod
    def dump_yaml_feature(cls, parent_dir):
        name = '-'.join([s.lower() for s in cls.get_title().split()])
        cls.dump_yaml(cls.as_yaml(), os.path.join(parent_dir, f'{name}.yml'))

    @classmethod
    def as_yaml(cls):
        story = '\n'.join(map(str.strip, cls.__doc__.strip('\n ').splitlines()))
        scs = {to_sentence(re.sub('test_', '', name, 1)):
               strip_lines(getattr(cls, name).__doc__.splitlines())
               for name in cls.get_own_scenario_names()}

        return collections.OrderedDict([
            ('Title', cls.get_title()), ('Story', literal(story)), ('Scenarios', scs)
        ] + [(to_sentence(n), v) for n, v in cls.get_own_class_attrs().items()])

    @classmethod
    def get_title(cls):
        return re.sub(r'[A-Z]', lambda m: f' {m.group()}', extract_name(cls.__name__)).strip()

    @classmethod
    def get_own_scenario_names(cls):
        return [n for n, v in inspect.getmembers(
            cls, lambda x: getattr(x, '__name__', None) in cls.steps.scenarios
            and f'\n    def {x.__name__}' in inspect.getsource(cls))]

    @classmethod
    def get_own_class_attrs(cls):
        return dict(filter(lambda it: f'\n    {it[0]} = ' in inspect.getsource(cls),
                           inspect.getmembers(cls)))

    @classmethod
    def log_scenario_run(cls, name, step_logs, symbol):
        cls.steps.run_number += 1
        cls.steps.scenarios[name].append((cls.steps.run_number, symbol))
        cls.steps.logger.info(
            f'{cls.steps.run_number} {symbol} {getattr(cls, name).__qualname__}:'
            + ''.join([f'\n  {cls.steps.run_number}.{n + 1} - {text}'
                       for n, (o, text) in enumerate(step_logs)]))

    @abc.abstractmethod
    def run_steps(self, method_doc):
        """Run scenario steps from `method_doc` and return logs list"""

    def log_step_result(self, symbol, result, logs, step):
        logs.append((symbol, f'{datetime.datetime.utcnow()} {symbol} '
                             f'{step.name} {step.inputs} {TO} {result or ()}'))

        if symbol == OK and isinstance(result, tuple):
            for name, value in zip(step.output_names, result):
                self.steps.outputs[name].append(value)


try:
    import pytest_twisted
except ImportError:
    class BddTester(BddTesterABC):
        def run_steps(self, method_doc):
            logs = []
            for step in Step.steps(method_doc.splitlines(), self.steps.aliases):
                try:
                    result = getattr(self, step.name)(*step.inputs)
                    symbol = OK
                except Exception:
                    symbol = FAIL
                    result = exceptions.format_next_traceback()

                self.log_step_result(symbol, result, logs, step)

                if symbol == FAIL:
                    break
            return logs

else:
    class BddTester(BddTesterABC):
        @pytest_twisted.inlineCallbacks
        def run_steps(self, method_doc):
            logs = []
            for step in Step.steps(method_doc.splitlines(), self.steps.aliases):
                try:
                    result = yield getattr(self, step.name)(*step.inputs)
                    symbol = OK
                except Exception:
                    symbol = FAIL
                    result = exceptions.format_next_traceback()

                self.log_step_result(symbol, result, logs, step)

                if symbol == FAIL:
                    break
            return logs


class BaseTestCase:
    @classmethod
    def setup_class(cls):
        if cls.steps.validate:
            cls.steps.tester.validate()

        cls.steps.logger.info('_'*80)

    @classmethod
    def teardown_class(cls):
        if cls.steps.get_pending_runs():
            end_note = ''
        else:
            passed = f' ▌ {cls.steps.passed} {OK}' if cls.steps.passed else ''
            failed = f' ▌ {cls.steps.failed} {FAIL}' if cls.steps.failed else ''
            end_note = '\n' + COMPLETION_MSG + passed + failed

        cls.steps.logger.info(f'{cls.steps}{end_note}')

    def teardown_method(self):
        self.steps.reset_outputs()
