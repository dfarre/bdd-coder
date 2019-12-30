import collections
import functools
import importlib
import inspect
import itertools
import os
import re
import subprocess

from bdd_coder import BASE_TEST_CASE_NAME
from bdd_coder import BASE_TESTER_NAME

from bdd_coder import exceptions
from bdd_coder import stock
from bdd_coder import features

from bdd_coder.coder import text_utils

from bdd_coder.tester import tester

DEFAULT_BASE_TEST_CASE = 'unittest.TestCase'
BDD_TEST_CASE_PATH = 'tester.BaseTestCase'
BDD_TESTER_PATH = 'tester.BddTester'


class FeatureClassCoder:
    def __init__(self, class_name, features_spec):
        self.class_name, self.spec = class_name, features_spec.features[class_name]

    @property
    def scenario_method_defs(self):
        return [self.make_scenario_method_def(name, scenario_spec)
                for name, scenario_spec in self.spec['scenarios'].items()]

    @property
    def step_method_defs(self):
        steps = features.FeaturesSpec.get_all_steps(self.spec)

        return self.make_step_method_defs_for([s for s in steps if s.own])

    @property
    def class_body(self):
        head = '\n'.join(self.extra_class_attrs)

        return ('' if head else '\n') + '\n\n'.join(
            ([head] if head else []) + self.scenario_method_defs + self.step_method_defs)

    @property
    def extra_class_attrs(self):
        return [f'{name} = {value}' for name, value in self.spec['extra_class_attrs'].items()]

    @property
    def source(self):
        return text_utils.make_class(
            self.class_name, self.spec['doc'], body=self.class_body, bases=self.bases)

    @property
    def bases(self):
        return (self.spec['bases'] or [f'base.{BASE_TESTER_NAME}']) + (
            [] if self.spec['inherited'] else [f'base.{BASE_TEST_CASE_NAME}'])

    @staticmethod
    def make_step_method_defs_for(steps_to_code):
        return [text_utils.make_method(
                    s.name, body=FeatureClassCoder.make_method_body(s.inputs, s.output_names),
                    args_text=', *args') for s in steps_to_code]

    @staticmethod
    def make_scenario_method_def(name, scenario_spec):
        return text_utils.make_method(
            ('' if scenario_spec['inherited'] else 'test_') + name,
            *scenario_spec['doc_lines'], decorators=('base.scenario',))

    @staticmethod
    def make_method_body(inputs, output_names):
        outputs_help = [
            'return ' + ''.join(f"'{output}', " for output in output_names)
        ] if output_names else []

        return '\n\n'.join([f'assert len(args) == {len(inputs)}'] + outputs_help)


class PackageCoder:
    def __init__(self, base_class=DEFAULT_BASE_TEST_CASE, specs_path='behaviour/specs',
                 tests_path='', test_module_name='stories', overwrite=False, logs_parent=''):
        if base_class == DEFAULT_BASE_TEST_CASE:
            self.base_test_case_bases = (BDD_TEST_CASE_PATH,)
            self.base_class_name = ''
        else:
            self.module_or_package_path, self.base_class_name = base_class.rsplit('.', 1)
            self.base_test_case_bases = (self.base_class_name, BDD_TEST_CASE_PATH)

        self.features_spec = features.FeaturesSpec(specs_path)
        self.tests_path = tests_path or os.path.join(os.path.dirname(specs_path), 'tests')
        self.logs_parent = (logs_parent or self.tests_path).rstrip('/')
        self.test_module_name = test_module_name
        self.overwrite = overwrite

    @property
    def story_class_defs(self):
        return [FeatureClassCoder(class_name, self.features_spec).source
                for class_name in self.features_spec.features]

    @property
    def aliases_def(self):
        dict_text = text_utils.indent(
            '\n'.join([f"'{k}': '{v}'," for k, v in sorted(
                self.features_spec.aliases.items(), key=lambda it: it[0])]))

        return f'MAP = {{\n{dict_text}\n}}'

    @property
    def base_method_defs(self):
        return [text_utils.make_method(name, args_text=', *args')
                for name in self.features_spec.base_methods]

    @property
    def base_class_defs(self):
        return [text_utils.make_class(
            BASE_TESTER_NAME, bases=(BDD_TESTER_PATH,), decorators=('steps',)
        ), text_utils.make_class(
            BASE_TEST_CASE_NAME, bases=self.base_test_case_bases,
            body='\n\n'.join(self.base_method_defs))]

    def pytest(self):
        stock.Process('pytest', '-vv', self.tests_path).write()

    def write_aliases_module(self):
        with open(os.path.join(self.tests_path, 'aliases.py'), 'w') as aliases_py:
            aliases_py.write(text_utils.rstrip(self.aliases_def) + '\n')

    @property
    def base_module_source(self):
        return '\n\n\n'.join([
            (f'from {self.module_or_package_path} import {self.base_class_name}\n\n'
             if self.base_class_name else '') + (
                'from bdd_coder.tester import decorators\n'
                'from bdd_coder.tester import tester\n\n'
                'from . import aliases\n\n'
                f"steps = decorators.Steps(aliases.MAP, '{self.logs_parent}')\n"
                "scenario = decorators.Scenario(steps)")
        ] + self.base_class_defs)

    def create_tester_package(self):
        exceptions.makedirs(self.tests_path, exist_ok=self.overwrite)

        with open(os.path.join(self.tests_path, '__init__.py'), 'w') as init_py:
            init_py.write('')

        with open(os.path.join(self.tests_path, 'base.py'), 'w') as base_py:
            base_py.write(text_utils.rstrip(self.base_module_source) + '\n')

        with open(os.path.join(self.tests_path, f'test_{self.test_module_name}.py'),
                  'w') as test_py:
            test_py.write(text_utils.rstrip('\n\n\n'.join(
                ['from . import base'] + self.story_class_defs)) + '\n')

        self.write_aliases_module()
        self.pytest()


class ClassPiece(stock.Repr):
    scenario_delimiter = '@base.scenario'

    def __init__(self, text):
        self.name, self.head, self.scenarios, self.tail = \
                                    self.split_class(text_utils.rstrip(text))

    def __str__(self):
        scenarios = '\n\n'.join(self.scenarios.values())
        scenarios_text = f'\n\n*** Scenarios ***\n{scenarios}' if self.scenarios else ''

        return f'*** Head ***\n{self.head}{scenarios_text}'

    @property
    def source(self):
        return text_utils.rstrip('\n\n'.join(list(map(text_utils.rstrip, itertools.chain(
            [self.head], self.scenarios.values(), self.tail)))))

    @classmethod
    def split_class(cls, text):
        name = cls.get_class_name(text)
        pieces = map(str.strip, text.split(cls.scenario_delimiter))
        top_item = next(pieces)
        scenarios, tail_pieces = collections.OrderedDict(), []

        for s in pieces:
            text = f'    {cls.scenario_delimiter}\n    {s}'
            scenario_text, _, scenario_name, tail = cls.match_scenario_piece(text)
            scenarios[scenario_name] = scenario_text

            if tail.strip():
                tail_pieces.append(tail.strip('\n'))

        return name, top_item, scenarios, tail_pieces

    @staticmethod
    def get_class_name(class_text):
        return re.match(r'^class ([A-Za-z]+)', class_text).groups()[0]

    @staticmethod
    def match_scenario_piece(text):
        match = re.match(
            r'^(    @base\.scenario\n    def (test_)?([^(]+)\(self\):\n'
            rf'{" "*8}"""\n.+?\n{" "*8}""")(.*)$', text, flags=re.DOTALL)

        return match.groups()


class TestModule(stock.Repr):
    class_delimiter = '\n\n\nclass '
    required_flake8_codes = [
        'E111', 'E301', 'E302', 'E303', 'E304', 'E701', 'E702', 'F999', 'W291', 'W293']

    def __init__(self, filename):
        self.flake8(filename)
        self.filename = filename
        self.tmp_filename = f'tmp_split_{id(self)}.py'

        with open(filename) as py_file:
            self.head, self.pieces = self.split_module(text_utils.rstrip(py_file.read()))

    def __str__(self):
        pieces = '\n\n'.join([str(cp) for cp in self.pieces.values()])

        return f'***** Head *****\n{self.head}\n\n***** Pieces *****\n{pieces}'

    def __del__(self):
        if os.path.exists(self.tmp_filename):
            os.remove(self.tmp_filename)

    def transform(self, *mutations):
        for mutate in mutations:
            mutate(self.pieces)

        self.validate()

    def validate(self):
        with open(self.tmp_filename, 'w') as tmp_file:
            tmp_file.write(self.source)

        self.flake8(self.tmp_filename)

    def write(self):
        with open(self.filename, 'w') as py_file:
            py_file.write(self.source + '\n')

    @property
    def source(self):
        return text_utils.rstrip('\n\n\n'.join([self.head] + [
            class_piece.source for class_piece in self.pieces.values()]))

    def flake8(cls, filename):
        try:
            subprocess.check_output([
                'flake8', '--select=' + ','.join(cls.required_flake8_codes), filename])
        except subprocess.CalledProcessError as error:
            # import ipdb; ipdb.set_trace()
            raise exceptions.Flake8Error(error.stdout.decode())

    @classmethod
    def split_module(cls, source):
        pieces = map(str.strip, source.split(cls.class_delimiter))
        head = next(pieces)
        class_pieces = [ClassPiece(f'class {s}') for s in pieces]

        return head, collections.OrderedDict([(cp.name, cp) for cp in class_pieces])


class PackagePatcher(PackageCoder):
    default_specs_dir_name = 'specs'

    def __init__(self, test_module='behaviour.tests.test_stories', specs_path=''):
        """May raise `Flake8Error`"""
        self.tests_path = os.path.dirname(test_module.replace('.', '/'))
        self.test_module_name = test_module.rsplit('.', 1)[-1]
        self.test_module = test_module
        self.splits = {name: TestModule(os.path.join(self.tests_path, f'{name}.py'))
                       for name in ['base', self.test_module_name]}
        self.old_specs = self.base_tester.features_spec()
        self.new_specs = features.FeaturesSpec(specs_path or os.path.join(
            os.path.dirname(self.tests_path), self.default_specs_dir_name))

        old_scenarios = self.old_specs.get_scenarios(self.old_specs.features)
        new_scenarios = self.new_specs.get_scenarios(self.new_specs.features)
        new_classes = set(new_scenarios.values()) - set(old_scenarios.values())
        new_features = collections.OrderedDict([
            (cn, spec) for cn, spec in self.new_specs.features.items()
            if cn in new_classes])

        self.empty_classes = set(old_scenarios.values()) - set(new_scenarios.values())
        self.added_scenarios = {class_name: collections.OrderedDict(sorted(filter(
            lambda it: it[0] in set(new_scenarios) - set(old_scenarios),
            self.new_specs.features[class_name]['scenarios'].items()),
            key=lambda it: it[0])) for class_name in new_scenarios.values()
            if class_name not in new_classes}
        self.removed_scenarios = {
            n: old_scenarios[n] for n in set(old_scenarios) - set(new_scenarios)}
        self.updated_scenarios = {
            n: new_scenarios[n] for n in set(old_scenarios) & set(new_scenarios)}
        self.features_spec = collections.namedtuple('features_spec', [
            'features', 'aliases', 'base_methods'])
        self.features_spec.features = new_features
        self.features_spec.aliases = {**self.old_specs.aliases, **self.new_specs.aliases}
        self.features_spec.base_methods = (
            set(self.new_specs.base_methods) - set(self.old_specs.base_methods))

    @property
    def base_tester(self):
        return get_base_tester(self.test_module)

    def get_tester(self, class_name):
        return getattr(importlib.import_module(self.test_module), class_name)

    def patch_module(self, module_name, *mutations):
        self.splits[module_name].transform(*mutations)
        self.splits[module_name].write()

    def remove_scenarios(self, pieces):
        for name, class_name in self.removed_scenarios.items():
            del pieces[class_name].scenarios[name]

    def update_scenarios(self, pieces):
        for name, class_name in self.updated_scenarios.items():
            spec = self.new_specs.features[class_name]['scenarios'][name]
            pieces[class_name].scenarios[name] = text_utils.indent(
                FeatureClassCoder.make_scenario_method_def(name, spec))

    def add_scenarios(self, pieces):
        for class_name, scenarios in self.added_scenarios.items():
            new_scenarios = {name: text_utils.indent(
                FeatureClassCoder.make_scenario_method_def(name, spec))
                for name, spec in scenarios.items()}
            pieces[class_name].scenarios.update(new_scenarios)

    def add_new_stories(self, pieces):
        pieces.update({cp.name: cp for cp in (
            ClassPiece(text) for text in self.story_class_defs)})

    def sort_hierarchy(self, pieces):
        for class_name, piece in self.yield_sorted_pieces(pieces):
            pieces[class_name] = piece
            pieces.move_to_end(class_name)

        for class_name in self.empty_classes:
            self.update_bases(class_name, f'base.{BASE_TESTER_NAME}', pieces)

    def yield_sorted_pieces(self, pieces):
        for name, bases in self.new_specs.class_bases:
            bases_code = ', '.join(FeatureClassCoder(name, self.new_specs).bases)
            self.update_bases(name, bases_code, pieces)

            yield name, pieces[name]

    @staticmethod
    def update_bases(name, bases_code, pieces):
        pieces[name].head = re.sub(
            fr'class {name}\([A-Za-z., ]+\):', f'class {name}({bases_code}):',
            pieces[name].head, 1)

    def add_new_steps(self, class_name, pieces):
        tester = self.get_tester(class_name)
        steps = self.new_specs.get_all_steps(self.new_specs.features[class_name])
        pieces[class_name].tail.extend(map(
            text_utils.indent, FeatureClassCoder.make_step_method_defs_for(filter(
                lambda s: s.own and not hasattr(tester, s.name), steps))))

    def add_base_methods(self, pieces):
        pieces[BASE_TEST_CASE_NAME].tail.extend(map(text_utils.indent, self.base_method_defs))

    def patch(self):
        self.patch_module(
            self.test_module_name,
            self.remove_scenarios, self.update_scenarios, self.add_scenarios,
            self.add_new_stories, self.sort_hierarchy, *[
                functools.partial(self.add_new_steps, subclass.__name__)
                for subclass in self.base_tester.subclasses_down()
                if subclass.__name__ in self.new_specs.features])
        self.patch_module('base', self.add_base_methods)
        self.write_aliases_module()
        self.pytest()


def get_base_tester(test_module_path):
    try:
        test_module = importlib.import_module(test_module_path)
    except ModuleNotFoundError:
        raise exceptions.StoriesModuleNotFoundError(test_module=test_module_path)

    if not hasattr(test_module, 'base'):
        raise exceptions.BaseModuleNotFoundError(test_module=test_module)

    base_tester = {obj for name, obj in inspect.getmembers(test_module.base)
                   if inspect.isclass(obj) and tester.BddTester in obj.__bases__}

    if not len(base_tester) == 1:
        raise exceptions.BaseTesterNotFoundError(test_module=test_module, set=base_tester)

    return base_tester.pop()
