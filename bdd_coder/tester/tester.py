import collections
import datetime
import inspect
import os
import re
import shutil
import traceback
import unittest
import yaml

from bdd_coder import SubclassesMixin
from bdd_coder import strip_lines
from bdd_coder import to_sentence
from bdd_coder import FAIL, OK, COMPLETION_MSG

from bdd_coder.coder import features


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


class BddTester(YamlDumper, SubclassesMixin):
    """
    To be decorated with `Steps`, and employed with methods decorated with
    `scenario` - mixes with a subclass of `BaseTestCase` to run test methods
    """

    @classmethod
    def get_features_spec(cls):
        parent_dir = '.tmp-specs'
        cls.dump_yaml_specs(parent_dir)
        specs = features.FeaturesSpec(parent_dir)
        shutil.rmtree(parent_dir)

        return specs

    @classmethod
    def validate_bases(cls, features_spec):
        try:
            for (klass, bases), (name, bases_names) in zip(
                    cls.subclasses_down().items(), features_spec.class_bases):
                assert klass.__name__ == name, f'{klass.__name__} != {name}'

                own_bases = set(bases)
                own_bases.discard(cls)
                base_test_cases = [b for b in own_bases if issubclass(b, BaseTestCase)]

                if features_spec.features[name]['inherited']:
                    assert len(base_test_cases) == 0, 'Unexpected ' \
                        f'{BaseTestCase.__name__} subclass in {klass.__name__}'
                else:
                    assert len(base_test_cases) == 1, 'Expected one ' \
                        f'{BaseTestCase.__name__} subclass in {klass.__name__}'

                    own_bases.remove(base_test_cases[0])

                own_bases_names = {b.__name__ for b in own_bases}

                assert own_bases_names == bases_names, \
                    f'Bases {own_bases_names} defined in {klass.__name__} do not ' \
                    f'match the specified ones {bases_names}'
        except AssertionError as error:
            return str(error)

    @classmethod
    def dump_yaml_specs(cls, parent_dir, overwrite=False):
        os.makedirs(parent_dir, exist_ok=overwrite)
        features_path = os.path.join(parent_dir, 'features')
        os.makedirs(features_path, exist_ok=overwrite)

        cls.dump_yaml_aliases(cls.steps.aliases, parent_dir)

        for tester_subclass in cls.subclasses_down():
            tester_subclass.dump_yaml_feature(features_path)

    @classmethod
    def dump_yaml_feature(cls, parent_dir):
        story = '\n'.join(map(str.strip, cls.__doc__.strip('\n ').splitlines()))
        scenarios = {to_sentence(re.sub('test_', '', name, 1)):
                     strip_lines(getattr(cls, name).__doc__.splitlines())
                     for name in cls.get_own_scenario_names()}
        ordered_dict = collections.OrderedDict([
            ('Title', cls.get_title()), ('Story', literal(story)), ('Scenarios', scenarios)
        ] + [(to_sentence(n), v) for n, v in cls.get_own_class_attrs().items()])
        name = '-'.join([s.lower() for s in cls.get_title().split()])
        cls.dump_yaml(ordered_dict, os.path.join(parent_dir, f'{name}.yml'))

    @classmethod
    def get_title(cls):
        return re.sub(r'[A-Z]', lambda m: f' {m.group()}', cls.__name__).strip()

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
        cls.steps.write_to_history(f'{cls.steps.run_number} {symbol} {cls.__name__}.{name}:'
                                   + ''.join([f'\n  {cls.steps.run_number}.{n+1} - {text}'
                                              for n, (o, text) in enumerate(step_logs)]))

    def run_steps(self, method_doc):
        for method_name, inputs, output_names in self.steps.get_step_specs(method_doc):
            try:
                symbol, output = OK, getattr(self, method_name)(*inputs) or ()
            except Exception:
                symbol, output = FAIL, traceback.format_exc()
            else:
                for name, value in zip(output_names, output):
                    self.steps.outputs[name].append(value)

            yield symbol, (f'{datetime.datetime.utcnow()} {symbol} '
                           f'{method_name} {inputs} |--> {output}')

            if symbol == FAIL:
                break


class BaseTestCase(unittest.TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()

        if cls.steps.get_pending_runs():
            end_note = ''
        else:
            passed = f' ▌ {cls.steps.passed} {OK}' if cls.steps.passed else ''
            failed = f' ▌ {cls.steps.failed} {FAIL}' if cls.steps.failed else ''
            end_note = '\n\n' + COMPLETION_MSG + passed + failed

        cls.steps.write_to_history(f'{cls.steps}{end_note}')

    def tearDown(self):
        self.steps.reset_outputs()
