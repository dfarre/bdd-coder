import collections
import inspect
import os
import re
import shutil
import sys
import yaml

import pytest

from bdd_coder import exceptions
from bdd_coder import features
from bdd_coder import stock

from bdd_coder.text_utils import extract_name
from bdd_coder.text_utils import strip_lines
from bdd_coder.text_utils import to_sentence

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


class BddTester(YamlDumper, stock.SubclassesMixin):
    """
    To be decorated with `Gherkin`
    """
    tmp_dir = '.tmp-specs'

    @classmethod
    def __init_subclass__(cls):
        if not hasattr(cls, 'gherkin'):
            return

        for name, scenario in cls.gherkin.scenarios[cls.__name__].items():
            for step in scenario.steps:
                try:
                    step_method = getattr(cls, step.name)
                except AttributeError:
                    raise exceptions.InconsistentClassStructure(
                        error=f'method {step.name} not found')

                step.method_qualname = step_method.__qualname__

                if step_method.__qualname__ in cls.gherkin:
                    step.doc_scenario = cls.gherkin[step_method.__qualname__]
                else:
                    setattr(cls, step.fixture_name, step(step_method))

        for scenario in filter(lambda s: not s.ready,
                               cls.gherkin.scenarios[cls.__name__].values()):
            setattr(cls, scenario.name, scenario(getattr(cls, scenario.name)))

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
            own_bases_names = {extract_name(b.__name__) for b in own_bases}

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

        cls.dump_yaml_aliases(cls.gherkin.aliases, parent_dir)

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
        return list(cls.gherkin.scenarios[cls.__name__])

    @classmethod
    def get_own_class_attrs(cls):
        return dict(filter(lambda it: f'\n    {it[0]} = ' in inspect.getsource(cls),
                           inspect.getmembers(cls)))

    @classmethod
    def setup_class(cls):
        if cls.gherkin.validate:
            cls.gherkin.BddTester.validate()

    @pytest.fixture(autouse=True)
    def fixture_setup(self, request):
        self.gherkin.new_run(request.node.name, request.function.scenario)
        self.pytest_request = request
        self.gherkin.reset_outputs()

    @property
    def current_run(self):
        return self.gherkin.test_runs[self.pytest_request.node.name]

    def get_output(self, name, index=-1):
        return self.gherkin.outputs[name][index]
