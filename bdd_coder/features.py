import collections
import copy
import itertools
import json
import os
import re
import yaml

from bdd_coder import exceptions
from bdd_coder import stock

from bdd_coder.text_utils import make_class_head
from bdd_coder.text_utils import sentence_to_name
from bdd_coder.text_utils import strip_lines
from bdd_coder.text_utils import I_REGEX, O_REGEX, PARAM_REGEX, TO

MAX_INHERITANCE_LEVEL = 100


class StepSpec(stock.Repr):
    @classmethod
    def generate_steps(cls, lines, *args, **kwargs):
        return (cls(line, i, *args, **kwargs) for i, line in enumerate(strip_lines(lines)))

    def __init__(self, text, ordinal, aliases):
        self.text = text.strip().split(maxsplit=1)[1].strip()
        self.ordinal = ordinal
        self.aliases = aliases
        self.own = False
        self.validate()

    def __str__(self):
        own = 'i' if self.own else 'o'
        output_names = ', '.join(self.output_names)
        param_names = ', '.join(self.param_names)

        return f'({own}) {self.name} [{param_names}] {TO} ({output_names})'

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False

        return (self.text, self.ordinal, self.own) == (other.text, other.ordinal, other.own)

    def validate(self):
        inames, onames = self.param_names, self.output_names
        has_repeated_inputs = len(set(inames)) < len(inames)
        has_repeated_outputs = len(set(onames)) < len(onames)

        if any([has_repeated_inputs, has_repeated_outputs]):
            raise exceptions.FeaturesSpecError(f'Repeated parameter names in {self}')

    @property
    def name(self):
        method = sentence_to_name(re.sub(I_REGEX, '', self.text))

        return self.aliases.get(method, method)

    @property
    def inputs(self):
        return re.findall(I_REGEX, self.text)

    @property
    def param_names(self):
        return re.findall(PARAM_REGEX, self.text)

    @property
    def output_names(self):
        return tuple(sentence_to_name(s) for s in re.findall(O_REGEX, self.text))


class FeaturesSpec(stock.Repr):
    @classmethod
    def from_specs_dir(cls, specs_path):
        """
        Constructs feature class specifications to be employed by the coders.
        Raises `FeaturesSpecError` for detected inconsistencies
        """
        aliases = cls.get_aliases(specs_path)
        prepared_specs = list(cls.yield_prepared_specs(specs_path, aliases))
        duplicates_errors = list(filter(None, (
            cls.check_if_duplicate_class_names(prepared_specs),
            cls.check_if_duplicate_scenarios(prepared_specs))))

        if duplicates_errors:
            raise exceptions.FeaturesSpecError('\n'.join(duplicates_errors))

        base_methods = set()
        features = cls.sets_to_lists(cls.sort(cls.simplify_bases(
            cls.check_if_cyclical_inheritance(cls.set_mro_bases(
                cls.prepare_inheritance_specs({
                    ft.pop('class_name'): ft for ft in prepared_specs
                }, aliases, base_methods))))))

        return cls(features, base_methods, aliases)

    def __init__(self, features, base_methods, aliases):
        self.features = features
        self.base_methods = sorted(base_methods)
        self.aliases = aliases

    def __str__(self):
        features = copy.deepcopy(self.features)

        for feature in features.values():
            for scenario in feature['scenarios'].values():
                scenario['steps'] = [str(step) for step in scenario['steps']]

        json_features = json.dumps(features, indent=4, ensure_ascii=False)
        bases = json.dumps(self.class_bases_text, indent=4)
        aliases = json.dumps(self.aliases, indent=4)
        base_methods = json.dumps(self.base_methods, indent=4)

        return '\n'.join([f'Class bases {bases}', f'Features {json_features}',
                          f'Aliases {aliases}', f'Base methods {base_methods}'])

    @property
    def scenarios(self):
        return self.get_scenarios(self.features)

    @property
    def class_bases(self):
        return list(map(lambda it: (it[0], set(it[1]['bases'])), self.features.items()))

    @property
    def class_bases_text(self):
        return list(map(lambda it: make_class_head(*it), self.class_bases))

    def get_test_class_name(self, class_name):
        return f'Test{class_name}' if self.is_test(class_name) else class_name

    def is_test(self, class_name):
        return not self.features[class_name]['inherited']

    @staticmethod
    def get_aliases(specs_path):
        with open(os.path.join(specs_path, 'aliases.yml')) as yml_file:
            yml_aliases = yaml.load(yml_file.read(), Loader=yaml.FullLoader)

        return dict(itertools.chain(*(zip(map(sentence_to_name, names), [
            sentence_to_name(alias)]*len(names))
            for alias, names in yml_aliases.items()))) if yml_aliases else {}

    @staticmethod
    def sets_to_lists(features):
        for feature_spec in features.values():
            feature_spec['bases'] = sorted(feature_spec['bases'])
            feature_spec['mro_bases'] = sorted(feature_spec['mro_bases'])

        return features

    @classmethod
    def prepare_inheritance_specs(cls, features, aliases, base_methods):
        for class_name, feature_spec in features.items():
            other_scenario_names = cls.get_scenarios(features, class_name)

            for step in cls.get_all_steps(feature_spec):
                if step.name in other_scenario_names:
                    other_class_name = other_scenario_names[step.name]
                    features[other_class_name]['inherited'] = True
                    features[other_class_name]['scenarios'][step.name]['inherited'] = True
                    feature_spec['mro_bases'].add(other_class_name)
                    feature_spec['bases'].add(other_class_name)
                elif step.name in feature_spec['scenarios']:
                    feature_spec['scenarios'][step.name]['inherited'] = True
                elif step.name in aliases.values():
                    base_methods.add(step.name)
                else:
                    step.own = True

        return features

    @classmethod
    def yield_prepared_specs(cls, specs_path, aliases):
        features_path = os.path.join(specs_path, 'features')

        for story_yml_name in os.listdir(features_path):
            with open(os.path.join(features_path, story_yml_name)) as feature_yml:
                yml_feature = yaml.load(feature_yml.read(), Loader=yaml.FullLoader)

            feature = {
                'class_name': cls.title_to_class_name(yml_feature.pop('Title')),
                'bases': set(), 'mro_bases': set(), 'inherited': False, 'scenarios': {
                    sentence_to_name(title): {
                        'title': title, 'inherited': False,  'doc_lines': lines,
                        'steps': tuple(StepSpec.generate_steps(lines, aliases))}
                    for title, lines in yml_feature.pop('Scenarios').items()},
                'doc': yml_feature.pop('Story')}
            feature['extra_class_attrs'] = {
                sentence_to_name(key): value for key, value in yml_feature.items()}

            yield feature

    @staticmethod
    def simplify_bases(features):
        for name, spec in filter(lambda it: len(it[1]['bases']) > 1, features.items()):
            bases = set(spec['bases'])

            for base_name in spec['bases']:
                bases -= bases & features[base_name]['bases']

            spec['bases'] = bases

        return features

    @staticmethod
    def check_if_cyclical_inheritance(features):
        for class_name, feature_spec in features.items():
            for base_class_name in feature_spec['mro_bases']:
                if class_name in features[base_class_name]['mro_bases']:
                    raise exceptions.FeaturesSpecError(
                        'Cyclical inheritance between {0} and {1}'.format(*sorted([
                            class_name, base_class_name])))

        return features

    @staticmethod
    def sort(features):
        """
        Sort (or try to sort) the features so that tester classes can be
        consistently defined.

        `MAX_INHERITANCE_LEVEL` is a limit for debugging, to prevent an
        infinite loop here, which should be forbidden by previous validation
        in the constructor
        """
        bases = {class_name: {
            'bases': spec['bases'], 'ordinal': 0 if not spec['bases'] else 1}
            for class_name, spec in features.items()}

        def get_of_level(ordinal):
            return {name for name in bases if bases[name]['ordinal'] == ordinal}

        level = 1

        while level < MAX_INHERITANCE_LEVEL:
            names = get_of_level(level)

            if not names:
                break

            level += 1

            for cn, bs in filter(lambda it: it[1]['bases'] & names, bases.items()):
                bs['ordinal'] = level
        else:
            raise AssertionError('Cannot sort tester classes to be defined!')

        return collections.OrderedDict(sorted(
            features.items(), key=lambda it: bases[it[0]]['ordinal']))

    @staticmethod
    def set_mro_bases(features):
        for name, spec in features.items():
            spec['mro_bases'].update(*(features[cn]['bases'] for cn in spec['bases']))
            spec['mro_bases'].discard(name)

        return features

    @staticmethod
    def check_if_duplicate_class_names(prepared_specs):
        repeated = list(map(
            lambda it: it[0], filter(lambda it: it[1] > 1, collections.Counter(
                [spec['class_name'] for spec in prepared_specs]).items())))

        if repeated:
            return f'Duplicate titles are not supported, {repeated}'

    @staticmethod
    def check_if_duplicate_scenarios(prepared_specs):
        scenarios = list(itertools.chain(*(
            [(nm, spec['class_name']) for nm in spec['scenarios']]
            for spec in prepared_specs)))
        repeated = dict(map(
            lambda it: (it[0], [cn for nm, cn in scenarios if nm == it[0]]),
            filter(lambda it: it[1] > 1,
                   collections.Counter([nm for nm, cn in scenarios]).items())))

        if repeated:
            return f'Repeated scenario names are not supported, {repeated}'

    @staticmethod
    def get_scenarios(features, *exclude):
        return {name: class_name for name, class_name in itertools.chain(*(
            [(nm, cn) for nm in spec['scenarios']]
            for cn, spec in features.items() if cn not in exclude))}

    @staticmethod
    def get_all_steps(feature_spec):
        return itertools.chain(*(
            sc['steps'] for sc in feature_spec['scenarios'].values()))

    @staticmethod
    def title_to_class_name(title):
        return ''.join(map(str.capitalize, title.split()))
