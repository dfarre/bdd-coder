import collections
import functools
import importlib
import inspect
import itertools
import json
import os
import re

from bdd_coder import ParametersMixin
from bdd_coder import Process
from bdd_coder import Repr

from bdd_coder.coder import BASE_TESTER_NAME
from bdd_coder.coder import BASE_TEST_CASE_NAME
from bdd_coder.coder import features
from bdd_coder.coder import text_utils

from bdd_coder.tester import tester


class FeatureClassCoder:
    def __init__(self, class_name, spec):
        self.class_name, self.spec = class_name, spec

    def make_scenario_method_defs(self):
        return [self.make_scenario_method_def(name, scenario_spec)
                for name, scenario_spec in self.spec['scenarios'].items()]

    def make_step_method_defs(self):
        step_specs = features.FeaturesSpec.get_all_step_specs(self.spec)
        steps_to_code = {
            name: (inp, out) for name, inp, out, make_it in step_specs if make_it}

        return self.make_step_method_defs_for(steps_to_code)

    def make_class_body(self):
        return '\n'.join(self.make_extra_class_attrs() +
                         self.make_scenario_method_defs() + self.make_step_method_defs())

    def make_extra_class_attrs(self):
        return [f'{name} = {value}' for name, value in self.spec['extra_class_attrs'].items()]

    def make(self):
        return text_utils.make_class(
            self.class_name, self.spec['doc'], body=self.make_class_body(),
            bases=self.get_bases())

    def get_bases(self):
        return (self.spec['bases'] or [f'base.{BASE_TESTER_NAME}']) + (
            [] if self.spec['inherited'] else [f'base.{BASE_TEST_CASE_NAME}'])

    @staticmethod
    def make_step_method_defs_for(steps_to_code):
        return [text_utils.make_method(
                    name, body=FeatureClassCoder.make_method_body(inputs, output_names),
                    args_text=', *args')
                for name, (inputs, output_names) in steps_to_code.items()]

    @staticmethod
    def make_scenario_method_def(name, scenario_spec):
        return text_utils.make_method(
            ('' if scenario_spec['inherited'] else 'test_') + name,
            *scenario_spec['doc_lines'], decorators=('decorators.Scenario(base.steps)',))

    @staticmethod
    def make_method_body(inputs, output_names):
        outputs_help = [
            'return ' + ''.join(f"'{output}', " for output in output_names)
        ] if output_names else []

        return '\n\n'.join([f'assert len(args) == {len(inputs)}'] + outputs_help)


class PackageCoder(ParametersMixin):
    def __init__(self, base_class='unittest.TestCase', specs_path='behaviour/specs',
                 tests_path='', test_module_name='stories', overwrite=False, logs_parent=''):
        self.module_or_package_path, self.base_class_name = base_class.rsplit('.', 1)
        self.features_spec = features.FeaturesSpec(specs_path)
        self.tests_path = tests_path or os.path.join(os.path.dirname(specs_path), 'tests')
        self.logs_parent = logs_parent or self.tests_path
        self.test_module_name = test_module_name
        self.overwrite = overwrite

    def make_story_class_defs(self):
        return [FeatureClassCoder(class_name, spec).make()
                for class_name, spec in self.features_spec.features.items()]

    def make_aliases_def(self):
        dict_text = text_utils.indent(
            '\n'.join(f"'{k}': '{v}'," for k, v in self.features_spec.aliases.items()))

        return f'MAP = {{\n{dict_text}\n}}'

    def make_base_method_defs(self):
        return '\n'.join([text_utils.make_method(name, args_text=', *args')
                          for name in self.features_spec.base_methods])

    def make_base_class_defs(self):
        return '\n'.join([
            text_utils.make_class(BASE_TESTER_NAME, bases=('tester.BddTester',),
                                  decorators=('steps',)),
            text_utils.make_class(BASE_TEST_CASE_NAME, bases=(
                'tester.BaseTestCase', self.base_class_name),
                body=self.make_base_method_defs())])

    def pytest(self):
        Process('pytest', '-vv', self.tests_path).write()

    def write_aliases_module(self):
        with open(os.path.join(self.tests_path, 'aliases.py'), 'w') as aliases_py:
            aliases_py.write(text_utils.rstrip(self.make_aliases_def()))

    def create_tester_package(self):
        os.makedirs(self.tests_path, exist_ok=self.overwrite)

        with open(os.path.join(self.tests_path, '__init__.py'), 'w') as init_py:
            init_py.write('')

        with open(os.path.join(self.tests_path, 'base.py'), 'w') as base_py:
            base_py.write(text_utils.rstrip(
                f'from {self.module_or_package_path} import {self.base_class_name}\n\n'
                'from bdd_coder.tester import decorators\n'
                'from bdd_coder.tester import tester\n\n'
                'from . import aliases\n\n'
                f"steps = decorators.Steps(aliases.MAP, '{self.logs_parent}')\n"
                + self.make_base_class_defs()))

        with open(os.path.join(self.tests_path, f'test_{self.test_module_name}.py'),
                  'w') as test_py:
            test_py.write(text_utils.rstrip(
                'from bdd_coder.tester import decorators'
                '\n\nfrom . import base\n' + '\n'.join(self.make_story_class_defs())))

        self.write_aliases_module()
        self.pytest()


class Split(Repr):
    class_delimiter = '\n\n\nclass '

    def __init__(self, source, scenario_delimiter):
        self.scenario_delimiter = scenario_delimiter
        source = text_utils.rstrip(source)
        self.pieces = self._split(source)

        if not self.source == source:
            raise AssertionError(f'Cannot rejoin {self} into\n\n{self.source}')

    def __str__(self):
        return json.dumps(self.pieces, indent=4, ensure_ascii=False)

    @property
    def source(self):
        return text_utils.rstrip(self.class_delimiter.join([
            '\n\n'.join(filter(None, itertools.chain(*(
                (f'    {self.scenario_delimiter}    {s}' if s else '',
                 f'    {r}' if r else '') for s, r in texts.values())))).strip()
            for n, texts in self.pieces.items()]))

    def _split(self, source):
        return self._split_scenarios(self._get_piece_texts(source))

    def _get_piece_texts(self, source):
        texts = map(str.strip, source.split(self.class_delimiter))
        top_item = ('top_piece', {'top_piece': next(texts)})

        return collections.OrderedDict([top_item] + [(
            self.get_class_name(txt), collections.OrderedDict([
                (self.get_scenario_name(text), text)
                for text in map(str.strip, txt.split(self.scenario_delimiter))]))
            for txt in texts])

    def _split_scenarios(self, piece_texts):
        piece_texts['top_piece']['top_piece'] = ['', piece_texts['top_piece']['top_piece']]

        for class_name, piece in list(piece_texts.items())[1:]:
            piece_texts[class_name][class_name] = ['', piece_texts[class_name][class_name]]

            for name, text in list(piece.items())[1:]:
                regex, flags = self.scenario_regex(name)
                match = re.match(regex, text, flags=flags)
                piece_texts[class_name][name] = [
                    match.groups()[0] if match else '',
                    re.sub(regex, '', text, flags=flags).strip()]

        return piece_texts

    def transform(self, *mutations):
        for mutate in mutations:
            mutate(self.pieces)

    @staticmethod
    def scenario_regex(name):
        return (rf'^(def (test_)?{name}\(self\):\n{" "*8}"""\n.+?\n{" "*8}""")',
                re.DOTALL)

    @staticmethod
    def get_class_name(class_text):
        return re.match(r'^([A-Za-z]+)', class_text).groups()[0]

    @staticmethod
    def get_scenario_name(text):
        return re.sub(r'^def (test_)?', '', re.sub(r'\(.*\)', '', text.split(':', 1)[0]), 1)


class PackagePatcher(PackageCoder):
    default_specs_dir_name = 'specs'
    scenario_delimiter = '@decorators.Scenario(base.steps)\n'

    def __init__(self, test_module='behaviour.tests.test_stories', specs_path=''):
        self.tests_path = os.path.dirname(test_module.replace('.', '/'))
        self.test_module_name = test_module.rsplit('.', 1)[-1]
        self.test_module = test_module
        self.old_specs = self.base_tester.get_features_spec()
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
        split = self.split(module_name)
        split.transform(*mutations)

        with open(os.path.join(self.tests_path, f'{module_name}.py'), 'w') as py_file:
            py_file.write(text_utils.rstrip(split.source))

    def split(self, module_name):
        with open(os.path.join(self.tests_path, f'{module_name}.py')) as py_file:
            return Split(py_file.read(), self.scenario_delimiter)

    def remove_scenarios(self, pieces):
        for name, class_name in self.removed_scenarios.items():
            pieces[class_name][name][0] = ''

    def update_scenarios(self, pieces):
        for class_name, piece in list(pieces.items())[1:]:
            for name in filter(lambda n: n not in self.removed_scenarios, list(piece)[1:]):
                spec = self.new_specs.features[class_name]['scenarios'][name]
                piece[name][0] = text_utils.indent(
                    FeatureClassCoder.make_scenario_method_def(
                        name, spec).strip()[len(self.scenario_delimiter):]).strip()

    def add_scenarios(self, pieces):
        for class_name, scenarios in self.added_scenarios.items():
            codes = [(name, [text_utils.indent(
                FeatureClassCoder.make_scenario_method_def(
                    name, spec).strip()[len(self.scenario_delimiter):]).strip(),
                '']) for name, spec in scenarios.items()]
            items = iter(pieces[class_name].items())
            pieces[class_name] = collections.OrderedDict([next(items)] + codes + list(items))

    def add_new_stories(self, pieces):
        new_classes = Split('\n' + '\n'.join(self.make_story_class_defs()),
                            self.scenario_delimiter).pieces
        new_classes.pop('top_piece')
        pieces.update(new_classes)

    def sort_hierarchy(self, pieces):
        for class_name, piece in self.yield_sorted_pieces(pieces):
            pieces[class_name] = piece
            pieces.move_to_end(class_name)

        for class_name in self.empty_classes:
            self.update_bases(class_name, f'base.{BASE_TESTER_NAME}', pieces)

    def yield_sorted_pieces(self, pieces):
        for name, bases in self.new_specs.class_bases:
            bases_code = ', '.join(FeatureClassCoder(
                name, self.new_specs.features[name]).get_bases())
            self.update_bases(name, bases_code, pieces)

            yield name, pieces[name]

    @staticmethod
    def update_bases(name, bases_code, pieces):
        pieces[name][name][1] = re.sub(
            r'\([A-Za-z., ]+\):', f'({bases_code}):', pieces[name][name][1], 1)

    def add_new_steps(self, class_name, pieces):
        tester = self.get_tester(class_name)
        step_specs = self.new_specs.get_all_step_specs(self.new_specs.features[class_name])
        steps_to_code = {name: (inp, out) for name, inp, out, make_it in step_specs
                         if make_it and not hasattr(tester, name)}
        name, (_, tail) = next(reversed(pieces[class_name].items()))
        pieces[class_name][name][1] = tail + '\n' + text_utils.indent('\n'.join(
            FeatureClassCoder.make_step_method_defs_for(steps_to_code)))

    def add_base_methods(self, pieces):
        pieces[BASE_TEST_CASE_NAME][BASE_TEST_CASE_NAME][1] += '\n' + text_utils.indent(
            self.make_base_method_defs())

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


def get_base_tester(test_module):
    module = (importlib.import_module(test_module)
              if isinstance(test_module, str) else test_module)

    return {obj for name, obj in inspect.getmembers(module.base)
            if inspect.isclass(obj) and tester.BddTester in obj.__bases__}.pop()
