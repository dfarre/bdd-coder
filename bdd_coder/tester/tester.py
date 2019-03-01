import collections
import datetime
import inspect
import re
import unittest
import yaml

from bdd_coder import strip_lines
from bdd_coder import to_sentence
from bdd_coder import SUCCESS_MSG


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
    def dump_yaml_aliases(cls, aliases, path):
        alias_lists = collections.defaultdict(list)

        for item in aliases.items():
            name, alias = map(to_sentence, item)
            alias_lists[alias].append(name)

        cls.dump_yaml(dict(alias_lists), path)


class BddTester(YamlDumper):
    """
    To be decorated with `Steps`, and employed with methods decorated with
    `scenario` - mix with a subclass of `BaseTestCase` to run test methods
    """

    @classmethod
    def dump_yaml_feature(cls, path):
        story = '\n'.join(map(str.strip, cls.__doc__.strip('\n ').splitlines()))
        scenarios = {to_sentence(re.sub('test_', '', name, 1)):
                     strip_lines(getattr(cls, name).__doc__.splitlines())
                     for name in cls.get_own_scenarios()}
        ordered_dict = collections.OrderedDict([
            ('Title', cls.get_title()), ('Story', literal(story)), ('Scenarios', scenarios)])
        cls.dump_yaml(ordered_dict, path)

    @classmethod
    def get_title(cls):
        return re.sub(r'[A-Z]', lambda m: f' {m.group()}', cls.__name__).strip()

    @classmethod
    def get_own_scenarios(cls):
        return [n for n, _ in inspect.getmembers(cls)
                if n in cls.steps.scenarios and f'def {n}' in inspect.getsource(cls)]

    @classmethod
    def log_scenario_run(cls, name, step_logs):
        cls.steps.run_number += 1
        cls.steps.scenarios[name].append(cls.steps.run_number)
        cls.steps.write_to_history(f'{cls.steps.run_number} ✓ {cls.__name__}.{name}:'
                                   + ''.join([f'\n  {cls.steps.run_number}.{n+1} - {text}'
                                              for n, text in enumerate(step_logs)]))

    def run_scenario(self, method_doc):
        def run_step(method_name, inputs, output_names):
            output = getattr(self, method_name)(*inputs) or ()

            for name, value in zip(output_names, output):
                self.steps.outputs[name].append(value)

            return (f'{datetime.datetime.utcnow()} ✓ '
                    f'{method_name} {inputs} |--> {output}')

        return [run_step(*args) for args in self.steps.get_step_specs(method_doc)]


class BaseTestCase(unittest.TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()

        end_note = '' if cls.steps.get_pending_runs() else '\n\n' + SUCCESS_MSG
        cls.steps.write_to_history(f'{cls.__name__} - {cls.steps}{end_note}')

    def tearDown(self):
        self.steps.reset_outputs()
