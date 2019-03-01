import itertools
import json
import os
import yaml

from bdd_coder import BaseRepr
from bdd_coder import get_step_specs
from bdd_coder import sentence_to_name


class FeaturesSpec(BaseRepr):
    def __init__(self, specs_path):
        """Constructs feature class specifications to be employed by the coders"""
        self.specs_path = specs_path
        self.aliases = self._get_aliases()
        self.base_methods = set()
        self.features = self._set_inheritance_specs({
            ft.pop('class_name'): ft for ft in self._yield_prepared_features()})

    def __str__(self):
        features = json.dumps(self.features, indent=2, ensure_ascii=False)

        return f'Aliases {json.dumps(self.aliases, indent=4)}\nFeatures {features}'

    def _get_aliases(self):
        with open(os.path.join(self.specs_path, 'aliases.yml')) as yml_file:
            yml_aliases = yaml.load(yml_file.read())

        return dict(itertools.chain(*(
            zip(map(sentence_to_name, names), [sentence_to_name(alias)]*len(names))
            for alias, names in yml_aliases.items())))

    def _set_inheritance_specs(self, features):
        for class_name, feature_spec in features.items():
            other_scenario_names = self.get_scenarios(features, class_name)

            for step_spec in self.get_all_step_specs(feature_spec):
                if step_spec[0] in other_scenario_names:
                    step_spec.append(False)
                    other_class_name = other_scenario_names[step_spec[0]]
                    feature_spec['bases'].append(other_class_name)
                    features[other_class_name]['inherited'] = True
                    features[other_class_name]['scenarios'][step_spec[0]]['inherited'] = True
                elif step_spec[0] in self.aliases.values():
                    step_spec.append(False)
                    self.base_methods.add(step_spec[0])
                else:
                    step_spec.append(True)

        return features

    def _yield_prepared_features(self):
        features_path = os.path.join(self.specs_path, 'features')

        for story_yml_name in os.listdir(features_path):
            with open(os.path.join(features_path, story_yml_name)) as feature_yml:
                yml_feature = yaml.load(feature_yml.read())

            feature = {
                'class_name': self.title_to_class_name(yml_feature.pop('Title')),
                'bases': [], 'inherited': False, 'scenarios': {sentence_to_name(title): {
                    'title': title, 'inherited': False,  'doc_lines': steps,
                    'step_specs': get_step_specs(steps, self.aliases)}
                    for title, steps in yml_feature.pop('Scenarios').items()},
                'doc': yml_feature.pop('Story')}
            feature['extra_class_attrs'] = {
                sentence_to_name(key): value for key, value in yml_feature.items()}

            yield feature

    @staticmethod
    def get_scenarios(features, *exclude):
        return {name: class_name for name, class_name in itertools.chain(*(
            [(nm, cn) for nm in spec['scenarios']]
            for cn, spec in features.items() if cn not in exclude))}

    @staticmethod
    def get_all_step_specs(feature_spec):
        return itertools.chain(*(
            sc['step_specs'] for sc in feature_spec['scenarios'].values()))

    @staticmethod
    def title_to_class_name(title):
        return ''.join(map(str.capitalize, title.split()))
