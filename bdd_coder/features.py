import collections
import copy
import itertools
import json
import os
import yaml

from bdd_coder import Step
from bdd_coder import sentence_to_name
from bdd_coder import sentence_to_method_name

from bdd_coder import exceptions
from bdd_coder import stock

from bdd_coder.coder import MAX_INHERITANCE_LEVEL
from bdd_coder.coder import text_utils


class FeaturesSpec(stock.Repr):
    def __init__(self, specs_path):
        """
        Constructs feature class specifications to be employed by the coders.
        Raises `FeaturesSpecError` for detected inconsistencies
        """
        self.specs_path = specs_path
        self.aliases = self._get_aliases()
        self.base_methods = set()
        prepared_specs = list(self._yield_prepared_specs())
        duplicates_errors = list(filter(None, (
            self._check_if_duplicate_class_names(prepared_specs),
            self._check_if_duplicate_scenarios(prepared_specs))))

        if duplicates_errors:
            raise exceptions.FeaturesSpecError('\n'.join(duplicates_errors))

        self.features = self._sets_to_lists(self._sort(self._simplify_bases(
            self._check_if_cyclical_inheritance(self._set_mro_bases(
                self._prepare_inheritance_specs({
                    ft.pop('class_name'): ft for ft in prepared_specs}))))))
        self.base_methods = sorted(self.base_methods)
        self.class_bases = self._get_class_bases()

    def __str__(self):
        features = copy.deepcopy(self.features)

        for feature in features.values():
            for scenario in feature['scenarios'].values():
                scenario['steps'] = [str(step) for step in scenario['steps']]

        json_features = json.dumps(features, indent=4, ensure_ascii=False)
        bases = json.dumps(self.get_class_bases_text(), indent=4)
        aliases = json.dumps(self.aliases, indent=4)
        base_methods = json.dumps(self.base_methods, indent=4)

        return '\n'.join([f'Class bases {bases}', f'Features {json_features}',
                          f'Aliases {aliases}', f'Base methods {base_methods}'])

    def _get_aliases(self):
        with open(os.path.join(self.specs_path, 'aliases.yml')) as yml_file:
            yml_aliases = yaml.load(yml_file.read(), Loader=yaml.FullLoader)

        return dict(itertools.chain(*(zip(map(sentence_to_method_name, names), [
            sentence_to_method_name(alias)]*len(names))
            for alias, names in yml_aliases.items()))) if yml_aliases else {}

    def _sets_to_lists(self, features):
        for feature_spec in features.values():
            feature_spec['bases'] = sorted(feature_spec['bases'])
            feature_spec['mro_bases'] = sorted(feature_spec['mro_bases'])

        return features

    def _prepare_inheritance_specs(self, features):
        for class_name, feature_spec in features.items():
            other_scenario_names = self.get_scenarios(features, class_name)

            for step in self.get_all_steps(feature_spec):
                if step.name in other_scenario_names:
                    other_class_name = other_scenario_names[step.name]
                    feature_spec['bases'].add(other_class_name)
                    feature_spec['mro_bases'].add(other_class_name)
                    features[other_class_name]['inherited'] = True
                    features[other_class_name]['scenarios'][step.name]['inherited'] = True
                elif step.name in feature_spec['scenarios']:
                    feature_spec['scenarios'][step.name]['inherited'] = True
                elif step.name in self.aliases.values():
                    self.base_methods.add(step.name)
                else:
                    step.own = True

        return features

    def _yield_prepared_specs(self):
        features_path = os.path.join(self.specs_path, 'features')

        for story_yml_name in os.listdir(features_path):
            with open(os.path.join(features_path, story_yml_name)) as feature_yml:
                yml_feature = yaml.load(feature_yml.read(), Loader=yaml.FullLoader)

            feature = {
                'class_name': self.title_to_class_name(yml_feature.pop('Title')),
                'bases': set(), 'mro_bases': set(), 'inherited': False, 'scenarios': {
                    sentence_to_method_name(title): {
                        'title': title, 'inherited': False,  'doc_lines': lines,
                        'steps': tuple(Step.steps(lines, self.aliases))}
                    for title, lines in yml_feature.pop('Scenarios').items()},
                'doc': yml_feature.pop('Story')}
            feature['extra_class_attrs'] = {
                sentence_to_name(key): value for key, value in yml_feature.items()}

            yield feature

    def _simplify_bases(self, features):
        for name, spec in filter(lambda it: len(it[1]['bases']) > 1, features.items()):
            bases = set(spec['bases'])

            for base_name in spec['bases']:
                bases -= bases & features[base_name]['bases']

            spec['bases'] = bases

        return features

    def _check_if_cyclical_inheritance(self, features):
        for class_name, feature_spec in features.items():
            for base_class_name in feature_spec['mro_bases']:
                if class_name in features[base_class_name]['mro_bases']:
                    raise exceptions.FeaturesSpecError(
                        'Cyclical inheritance between {0} and {1}'.format(*sorted([
                            class_name, base_class_name])))

        return features

    def _sort(self, features):
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

    def _set_mro_bases(self, features):
        for name, spec in features.items():
            spec['mro_bases'].update(*(features[cn]['bases'] for cn in spec['bases']))
            spec['mro_bases'].discard(name)

        return features

    def _get_class_bases(self):
        return list(map(lambda it: (it[0], set(it[1]['bases'])), self.features.items()))

    def get_class_bases_text(self):
        return list(map(lambda it: text_utils.make_class_head(*it), self.class_bases))

    @staticmethod
    def _check_if_duplicate_class_names(prepared_specs):
        repeated = list(map(
            lambda it: it[0], filter(lambda it: it[1] > 1, collections.Counter(
                [spec['class_name'] for spec in prepared_specs]).items())))

        if repeated:
            return f'Duplicate titles are not supported, {repeated}'

    @staticmethod
    def _check_if_duplicate_scenarios(prepared_specs):
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
