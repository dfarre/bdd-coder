import os
import subprocess

from bdd_coder.coder import BASE_TESTER_NAME
from bdd_coder.coder import BASE_TEST_CASE_NAME
from bdd_coder.coder import features
from bdd_coder.coder import text_utils


def make_method_body(inputs, output_names):
    outputs_help = [
        'return ' + ''.join(f"'{output}', " for output in output_names)
    ] if output_names else []

    return '\n\n'.join([f'assert len(args) == {len(inputs)}'] + outputs_help)


class FeatureClassCoder:
    def __init__(self, class_name, spec):
        self.class_name, self.spec = class_name, spec

    def make_scenario_method_defs(self):
        return [text_utils.make_method(
            ('' if scenario_spec['inherited'] else 'test_') + name,
            *scenario_spec['doc_lines'], decorators=('decorators.Scenario(base.steps)',))
            for name, scenario_spec in self.spec['scenarios'].items()]

    def make_step_method_defs(self):
        step_specs = features.FeaturesSpec.get_all_step_specs(self.spec)
        steps_to_code = {
            name: (inp, out) for name, inp, out, make_it in step_specs if make_it}

        return [text_utils.make_method(
                    name, body=make_method_body(inputs, output_names),
                    args_text=', *args')
                for name, (inputs, output_names) in steps_to_code.items()]

    def make_class_body(self):
        return '\n'.join(self.make_extra_class_attrs() +
                         self.make_scenario_method_defs() + self.make_step_method_defs())

    def make_extra_class_attrs(self):
        return [f'{name} = {value}' for name, value in self.spec['extra_class_attrs'].items()]

    def make(self):
        bases = (self.spec['bases'] or [f'base.{BASE_TESTER_NAME}']) + (
            [] if self.spec['inherited'] else [f'base.{BASE_TEST_CASE_NAME}'])

        return text_utils.make_class(
            self.class_name, self.spec['doc'], body=self.make_class_body(), bases=bases)


class PackageCoder:
    def __init__(self, base_class='unittest.TestCase', specs_path='behaviour/specs/',
                 tests_path='', test_module_name='stories', logs_parent=''):
        self.module_or_package_path, self.base_class_name = base_class.rsplit('.', 1)
        self.features_spec = features.FeaturesSpec(specs_path)
        self.tests_path = tests_path or os.path.join(os.path.dirname(specs_path), 'tests')
        self.logs_parent = logs_parent or self.tests_path
        self.test_module_name = test_module_name

    @staticmethod
    def rstrip(text):
        return '\n'.join(list(map(str.rstrip, text.splitlines()))) + '\n'

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

    def create_tester_package(self):
        os.makedirs(self.tests_path)

        with open(os.path.join(self.tests_path, '__init__.py'), 'w') as init_py:
            init_py.write('')

        with open(os.path.join(self.tests_path, 'aliases.py'), 'w') as aliases_py:
            aliases_py.write(self.rstrip(self.make_aliases_def()))

        with open(os.path.join(self.tests_path, 'base.py'), 'w') as base_py:
            base_py.write(self.rstrip(
                f'from {self.module_or_package_path} import {self.base_class_name}\n\n'
                'from bdd_coder.tester import decorators\n'
                'from bdd_coder.tester import tester\n\n'
                'from . import aliases\n\n'
                f"steps = decorators.Steps(aliases.MAP, '{self.logs_parent}')\n"
                + self.make_base_class_defs()))

        with open(os.path.join(self.tests_path, f'test_{self.test_module_name}.py'),
                  'w') as test_py:
            test_py.write(self.rstrip(
                'from bdd_coder.tester import decorators'
                '\n\nfrom . import base\n' + '\n'.join(self.make_story_class_defs())))

        out = subprocess.run(['pytest', '-vv', self.tests_path], stdout=subprocess.PIPE)

        return out.stdout.decode()
