import itertools
import os
import yaml

from bdd_coder import get_step_specs
from bdd_coder import sentence_to_name


def indent(text, tabs=1):
    newspace = ' '*4*tabs
    text = text.replace('\n', '\n' + newspace)

    return newspace + text


def make_doc(*lines):
    text = '\n'.join(line.strip() for line in lines)

    return f'"""\n{text}\n"""'


def decorate(target, decorators):
    return '\n'.join([f'@{decorator}' for decorator in decorators] + [target])


def make_class_head(name, *doc_lines, inheritance='', decorators=()):
    doc = '\n' + indent(make_doc(*doc_lines)) if doc_lines else ''

    return '\n\n' + decorate(f'class {name}{inheritance}:{doc}', decorators)


def make_method(name, body='pass', decorators=()):
    return '\n' + indent(decorate(
        f'def {name}(self, *args, **kwargs):\n{indent(body)}', decorators))


class Coder:
    def __init__(self, base_class='unittest.TestCase', specs_path='behaviour/specs',
                 tests_path=''):
        self.module_or_package_path, self.base_class_name = base_class.rsplit('.', 1)
        self.specs_path = specs_path
        self.tests_path = tests_path or os.path.join(os.path.dirname(specs_path), 'tests')
        self.common_steps = self._get_common_steps()

    def _get_common_steps(self):
        with open(os.path.join(self.specs_path, 'steps.yml')) as yml_file:
            steps = yaml.load(yml_file.read())

        common_steps = {}

        for alias in steps:
            common_steps.update(dict(zip(map(sentence_to_name, steps[alias]),
                                         [sentence_to_name(alias)]*len(steps[alias]))))

        return common_steps

    def yield_story_class_defs(self):
        features_path = os.path.join(self.specs_path, 'features')

        for story_yml_path in os.listdir(features_path):
            yield StoryCoder(os.path.join(features_path, story_yml_path),
                             self.common_steps).make()

    def make_base_class_def(self):
        class_head = make_class_head(
            'BddApiTestCase', inheritance=f'({self.base_class_name})',
            decorators=('decorators.Steps(steps.MAP)',))
        method_defs = list(map(make_method, set(self.common_steps.values())))

        return '\n'.join([class_head] + method_defs)

    def make_common_steps_def(self):
        steps = indent('\n'.join(f"'{k}': '{v}'," for k, v in self.common_steps.items()))

        return f'MAP = {{\n{steps}\n}}'

    def create_package(self):
        os.makedirs(self.tests_path)

        with open(os.path.join(self.tests_path, '__init__.py'), 'w') as init_py:
            init_py.write('')

        with open(os.path.join(self.tests_path, 'steps.py'), 'w') as steps_py:
            steps_py.write(self.make_common_steps_def())

        with open(os.path.join(self.tests_path, 'base.py'), 'w') as base_py:
            base_py.write(
                f'from {self.module_or_package_path} import {self.base_class_name}\n\n'
                'from bdd_coder import decorators\n\n'
                'from . import steps\n'
                + self.make_base_class_def())

        with open(os.path.join(self.tests_path, 'test_features.py'), 'w') as test_py:
            test_py.write('from . import base\n\nfrom bdd_coder import decorators\n' +
                          '\n'.join(self.yield_story_class_defs()))


class StoryCoder:
    def __init__(self, story_yml_path, common_steps):
        with open(story_yml_path) as yml_file:
            self.feature = yaml.load(yml_file.read())

        self.common_steps = common_steps

    @staticmethod
    def title_to_class_name(title):
        return ''.join(map(str.capitalize, title.split()))

    @staticmethod
    def make_method_body(inputs, output_names):
        outputs = 'return ' + ''.join(f"'{output}', " for output in output_names)

        if inputs:
            inputs_tuple = ''.join(f"'{input}', " for input in inputs)

            return f'assert args == ({inputs_tuple})\n\n{outputs}'

        return outputs

    def make_scenario_method_defs(self):
        return ['\n' + indent(decorate(
            f'def test_{sentence_to_name(title)}(self):\n{indent(make_doc(*steps))}',
            ('decorators.scenario',))) for title, steps in self.feature['Scenarios'].items()]

    def make_step_method_defs(self):
        steps = itertools.chain(*self.feature['Scenarios'].values())
        step_specs = {name: (inp, out) for name, inp, out in get_step_specs(steps)
                      if name not in self.common_steps.values()}

        return [make_method(method_name, self.make_method_body(inputs, output_names))
                for method_name, (inputs, output_names) in step_specs.items()]

    def make_class_head(self):
        return make_class_head(
            self.title_to_class_name(self.feature['Title']), self.feature['Story'],
            inheritance='(base.BddApiTestCase)')

    def make_django_fixtures_class_attr(self):
        fixtures = ', '.join(f"'{sentence_to_name(fixture)}'"
                             for fixture in self.feature.get('Django fixtures', []))

        return indent(f'fixtures = [{fixtures}]') if fixtures else ''

    def make(self):
        return '\n'.join([self.make_class_head()] + [self.make_django_fixtures_class_attr()]
                         + self.make_scenario_method_defs() + self.make_step_method_defs())
