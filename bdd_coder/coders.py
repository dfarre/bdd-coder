import collections
import functools
import importlib
import inspect
import itertools
import os
import re
import subprocess

from bdd_coder import exceptions
from bdd_coder import stock
from bdd_coder import features
from bdd_coder import tester

from bdd_coder.text_utils import (
    BASE_TESTER_NAME, extract_name, strip_lines, indent, make_method,
    make_class, make_doc, rstrip)

BDD_TESTER_PATH = 'tester.BddTester'


class FeatureClassCoder:
    def __init__(self, class_name, features_spec):
        self.class_name = class_name
        self.features_spec = features_spec

    @property
    def spec(self):
        return self.features_spec.features[self.class_name]

    @property
    def test_class_name(self):
        return self.features_spec.get_test_class_name(self.class_name)

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
        return make_class(
            self.test_class_name, self.spec['doc'], body=self.class_body, bases=self.bases)

    @property
    def bases(self):
        return [
            self.features_spec.get_test_class_name(b) for b in self.spec['bases']
        ] if self.spec['bases'] else [f'base.{BASE_TESTER_NAME}']

    @staticmethod
    def make_step_method_defs_for(steps_to_code):
        return [make_method(
            s.name, body=FeatureClassCoder.make_method_body(s.param_names, s.output_names),
            args_text=''.join([f', {n}' for n in s.param_names])
        ) for s in stock.list_drop_duplicates(steps_to_code, lambda s: s.name)]

    @staticmethod
    def make_scenario_method_def(name, scenario_spec, parameters=''):
        return make_method(
            ('' if scenario_spec['inherited'] else 'test_') + name,
            *scenario_spec['doc_lines'], decorators=('base.gherkin.scenario()',))

    @staticmethod
    def make_method_body(param_names, output_names):
        return (
            'return ' + ''.join(f"'{output}', " for output in output_names)
        ) if output_names else 'pass'


class PackageCoder:
    logs_file_name = 'bdd_runs.log'

    def __init__(self, specs_path='behaviour/specs', tests_path='',
                 test_module_name='stories', overwrite=False, logs_path=''):
        self.features_spec = features.FeaturesSpec.from_specs_dir(specs_path)
        self.tests_path = tests_path or os.path.join(os.path.dirname(specs_path), 'tests')
        self.logs_path = (
            logs_path or os.path.join(self.tests_path, self.logs_file_name)).rstrip('/')
        self.test_module_name = test_module_name
        self.overwrite = overwrite

    @property
    def story_class_defs(self):
        return [FeatureClassCoder(class_name, self.features_spec).source
                for class_name in self.features_spec.features]

    @property
    def aliases_def(self):
        dict_text = indent(
            '\n'.join([f"'{k}': '{v}'," for k, v in sorted(
                self.features_spec.aliases.items(), key=lambda it: it[0])]))

        return f'MAP = {{\n{dict_text}\n}}'

    @property
    def base_method_defs(self):
        return [make_method(name, args_text=', *args')
                for name in self.features_spec.base_methods]

    @property
    def base_class_def(self):
        return make_class(
            BASE_TESTER_NAME, bases=(BDD_TESTER_PATH,), decorators=('gherkin',),
            body='\n\n'.join(self.base_method_defs))

    def pytest(self):
        stock.Process('pytest', '-vv', self.tests_path).write()

    def write_aliases_module(self):
        with open(os.path.join(self.tests_path, 'aliases.py'), 'w') as aliases_py:
            aliases_py.write(rstrip(self.aliases_def) + '\n')

    @property
    def base_module_source(self):
        return '\n\n\n'.join([
            'from bdd_coder import decorators\n'
            'from bdd_coder import tester\n\n'
            'from . import aliases\n\n'
            f"gherkin = decorators.Gherkin(aliases.MAP, logs_path='{self.logs_path}')",
            self.base_class_def])

    def create_tester_package(self, run_pytest=False):
        exceptions.makedirs(self.tests_path, exist_ok=self.overwrite)

        with open(os.path.join(self.tests_path, '__init__.py'), 'w') as init_py:
            init_py.write("import pytest\n\n"
                          "pytest.register_assert_rewrite(f'{__name__}.base')\n")

        with open(os.path.join(self.tests_path, 'base.py'), 'w') as base_py:
            base_py.write(rstrip(self.base_module_source) + '\n')

        with open(os.path.join(self.tests_path, f'test_{self.test_module_name}.py'),
                  'w') as test_py:
            test_py.write(rstrip('\n\n\n'.join(
                ['from . import base'] + self.story_class_defs)) + '\n')

        self.write_aliases_module()

        if run_pytest:
            self.pytest()


class ModulePiece(stock.Repr):
    scenario_delimiter = '@base.gherkin.scenario'

    def __init__(self, text, name_regex=r'[A-Za-z0-9]+'):
        rtext = rstrip(text)
        match = re.match(
            fr'^(@(.+))?class ({name_regex})(.*?):\n(    """(.+?)""")?(.*)$',
            rtext, flags=re.DOTALL)

        if match:
            decorators, _, name, bases, _, doc, body = match.groups()
            self.name = extract_name(name)
            self.class_head = f'{name}{bases or ""}'
            self.decorators = decorators or ''
            self.doc = '\n'.join(strip_lines(doc.splitlines())) if doc else None
            self.body_head, self.scenarios, self.tail = self.split_class_body(body)
            self.match = True
        else:
            self.match = False
            self.name, self.text = f'piece{id(self)}', rtext

    def __str__(self):
        if not self.match:
            return self.text

        scenarios = '\n\n'.join(self.scenarios.values())
        scenarios_text = f'\n\n-- Scenarios:\n{scenarios}' if self.scenarios else ''

        return f'-- Head:\n{self.head}{scenarios_text}'

    @property
    def source(self):
        if not self.match:
            return self.text

        return rstrip('\n\n'.join(list(map(rstrip, itertools.chain(
            [self.head], self.scenarios.values(), self.tail)))))

    @property
    def head(self):
        doc = [indent(make_doc(
            *self.doc.splitlines()))] if self.doc else []
        body_head = [self.body_head] if self.body_head else []

        return '\n'.join([
            f'{self.decorators}class {self.class_head}:'] + doc + body_head)

    @classmethod
    def split_class_body(cls, text):
        pieces = iter(text.strip('\n').split(cls.scenario_delimiter))
        body_head = next(pieces).rstrip()
        scenarios, tail_pieces = collections.OrderedDict(), []

        for s in pieces:
            scenario_text, _, scenario_name, tail = cls.match_scenario_piece(s.strip())
            scenarios[scenario_name] = scenario_text

            if tail.strip():
                tail_pieces.append(tail.strip('\n'))

        return body_head, scenarios, tail_pieces

    @classmethod
    def match_scenario_piece(cls, text):
        scenario_code = f'    {cls.scenario_delimiter}{text}'
        match = re.match(
            r'^(    @base\.gherkin\.scenario\(.*\)\n    def (test_)?([^(]+)\(self\):\n'
            rf'{" "*8}"""\n.+?\n{" "*8}""")(.*)$',
            scenario_code, flags=re.DOTALL)

        if match is None:
            raise exceptions.ScenarioMismatchError(code=scenario_code)

        return match.groups()


class TestModule(stock.Repr):
    required_flake8_codes = [
        'E111', 'E301', 'E302', 'E303', 'E304', 'E701', 'E702', 'F999', 'W291', 'W293']

    def __init__(self, filename, *class_names):
        self.filename = filename
        self.tmp_filename = f'tmp_split_{id(self)}.py'
        self.flake8(filename)
        self.name_regex = r'|'.join(class_names)

        with open(filename) as py_file:
            self.pieces = self.split_module(rstrip(py_file.read()))

    def __str__(self):
        return '\n\n-----\n'.join([str(p) for p in self.pieces.values()])

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
        return rstrip('\n\n\n'.join([
            piece.source for piece in self.pieces.values()]))

    def flake8(cls, filename):
        try:
            subprocess.check_output([
                'flake8', '--select=' + ','.join(cls.required_flake8_codes), filename])
        except subprocess.CalledProcessError as error:
            raise exceptions.Flake8Error(error.stdout.decode())

    def split_module(self, source):
        return collections.OrderedDict([(mp.name, mp) for mp in (
            ModulePiece(piece, self.name_regex) for piece in source.split('\n\n\n'))])


class PackagePatcher(PackageCoder):
    default_specs_dir_name = 'specs'

    def __init__(self, test_module='behaviour.tests.test_stories', specs_path=''):
        """May raise `Flake8Error`"""
        self.base_tester, self.test_module = get_base_tester(test_module)
        self.new_specs = features.FeaturesSpec.from_specs_dir(specs_path or os.path.join(
            os.path.dirname(self.tests_path), self.default_specs_dir_name))
        old_specs = self.base_tester.features_spec()

        self.splits = {'base': TestModule(
            os.path.join(self.tests_path, 'base.py'), BASE_TESTER_NAME
        ), self.test_module_name: TestModule(
            os.path.join(self.tests_path, f'{self.test_module_name}.py'),
            *(old_specs.get_test_class_name(n) for n in old_specs.features))}

        new_classes = (
            set(self.new_specs.scenarios.values()) - set(old_specs.scenarios.values()))
        new_features = collections.OrderedDict([
            (cn, spec) for cn, spec in self.new_specs.features.items()
            if cn in new_classes])

        self.empty_classes = (
            set(old_specs.scenarios.values()) - set(self.new_specs.scenarios.values()))
        self.added_scenarios = {class_name: collections.OrderedDict(sorted(filter(
            lambda it: it[0] in set(self.new_specs.scenarios) - set(old_specs.scenarios),
            self.new_specs.features[class_name]['scenarios'].items()),
            key=lambda it: it[0])) for class_name in self.new_specs.scenarios.values()
            if class_name not in new_classes}
        self.removed_scenarios = {n: old_specs.scenarios[n] for n in (
            set(old_specs.scenarios) - set(self.new_specs.scenarios))}
        self.updated_scenarios = {n: self.new_specs.scenarios[n] for n in (
            set(old_specs.scenarios) & set(self.new_specs.scenarios)
        ) if self.new_specs.scenarios[n] == old_specs.scenarios[n] and (
            old_specs.features[old_specs.scenarios[n]]['scenarios'][n] !=
            self.new_specs.features[self.new_specs.scenarios[n]]['scenarios'][n])}

        self.features_spec = features.FeaturesSpec(new_features, (
            set(self.new_specs.base_methods) - set(old_specs.base_methods)
        ), {**old_specs.aliases, **self.new_specs.aliases})

    @property
    def tests_path(self):
        return os.path.dirname(self.test_module.__file__)

    @property
    def test_module_name(self):
        return self.test_module.__name__.rsplit('.', 1)[-1]

    def get_tester(self, class_name):
        return getattr(self.test_module, class_name)

    def patch_module(self, module_name, *mutations):
        self.splits[module_name].transform(*mutations)
        self.splits[module_name].write()

    def remove_scenarios(self, pieces):
        for name, class_name in self.removed_scenarios.items():
            del pieces[class_name].scenarios[name]

    def update_scenarios(self, pieces):
        for name, class_name in self.updated_scenarios.items():
            spec = self.new_specs.features[class_name]['scenarios'][name]
            pieces[class_name].scenarios[name] = indent(
                FeatureClassCoder.make_scenario_method_def(name, spec))

    def add_scenarios(self, pieces):
        for class_name, scenarios in self.added_scenarios.items():
            new_scenarios = {name: indent(
                FeatureClassCoder.make_scenario_method_def(name, spec))
                for name, spec in scenarios.items()}
            pieces[class_name].scenarios.update(new_scenarios)

    def add_new_stories(self, pieces):
        pieces.update({cp.name: cp for cp in (
            ModulePiece(text) for text in self.story_class_defs)})

    def sort_hierarchy(self, pieces):
        for class_name, piece in self.yield_sorted_pieces(pieces):
            pieces[class_name] = piece
            pieces.move_to_end(class_name)

        for class_name in self.empty_classes:
            self.update_class_head(
                class_name, f'{class_name}(base.{BASE_TESTER_NAME})', pieces)

    def yield_sorted_pieces(self, pieces):
        for name, bases in self.new_specs.class_bases:
            class_coder = self.get_class_coder(name)
            class_head = f'{class_coder.test_class_name}({", ".join(class_coder.bases)})'
            self.update_class_head(name, class_head, pieces)

            yield name, pieces[name]

    def get_class_coder(self, name):
        return FeatureClassCoder(name, self.new_specs)

    @staticmethod
    def update_class_head(name, class_head, pieces):
        pieces[name].class_head = class_head

    def update_docs(self, pieces):
        for name in self.new_specs.features.keys() - self.features_spec.features.keys():
            pieces[name].doc = self.new_specs.features[name]['doc']

    def add_new_steps(self, class_name, pieces):
        tester = self.get_tester(class_name)
        steps = self.new_specs.get_all_steps(self.new_specs.features[class_name])
        pieces[class_name].tail.extend(map(
            indent, FeatureClassCoder.make_step_method_defs_for(filter(
                lambda s: s.own and not hasattr(tester, s.name), steps))))

    def add_base_methods(self, pieces):
        pieces[BASE_TESTER_NAME].tail.extend(map(indent, self.base_method_defs))

    def patch(self, run_pytest=False):
        self.patch_module(
            self.test_module_name,
            self.remove_scenarios, self.update_docs, self.update_scenarios,
            self.add_scenarios, self.add_new_stories, self.sort_hierarchy, *[
                functools.partial(self.add_new_steps, subclass.__name__)
                for subclass in self.base_tester.subclasses_down()
                if subclass.__name__ in self.new_specs.features])
        self.patch_module('base', self.add_base_methods)
        self.write_aliases_module()

        if run_pytest:
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

    return base_tester.pop(), test_module
