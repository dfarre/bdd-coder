from __future__ import annotations

from collections import Counter, OrderedDict

import itertools
import os
import pprint
import re

from typing import Iterable, Iterator, Optional

import yaml

from bdd_coder import exceptions
from bdd_coder import stock

from bdd_coder.text_utils import make_class_head, indent
from bdd_coder.text_utils import sentence_to_name
from bdd_coder.text_utils import strip_lines
from bdd_coder.text_utils import I_REGEX, O_REGEX, PARAM_REGEX, TO

MAX_INHERITANCE_LEVEL = 100


class StepSpec(stock.Repr, stock.Hashable):
    @classmethod
    def generate_steps(cls, lines: list[str], *args, **kwargs) -> Iterator[StepSpec]:
        return (cls(line, i, *args, **kwargs) for i, line in enumerate(strip_lines(lines)))

    def __init__(self, text: str, ordinal: int):
        self.text: str = text.strip().split(maxsplit=1)[1].strip()
        self.ordinal = ordinal
        self.is_local: bool = True
        self.is_scenario: bool = False
        self.method_qualname: str = ''
        self.validate()

    def __str__(self) -> str:
        mark = 's' if self.is_scenario else '+' if self.is_local else '-'
        output_names = ', '.join(self.output_names)
        param_names = ', '.join(self.param_names)

        return f'({mark}) {self.name} [{param_names}] {TO} ({output_names})'

    def eqkey(self) -> tuple[str, int, bool, bool]:
        return self.text, self.ordinal, self.is_local, self.is_scenario

    def validate(self):
        inames, onames = self.param_names, self.output_names
        has_repeated_inputs = len(set(inames)) < len(inames)
        has_repeated_outputs = len(set(onames)) < len(onames)

        if any([has_repeated_inputs, has_repeated_outputs]):
            raise exceptions.FeaturesSpecError(f'Repeated parameter names in {self}')

    def format_parameters(self, **kwargs) -> str:
        if not kwargs and not self.inputs:
            return ''

        text = '\n'.join(([f'    {", ".join(self.inputs)}'] if self.inputs else []) +
                         [f'    {n} = {repr(v)}' for n, v in kwargs.items()])

        return f'\n{text}'

    @property
    def name(self) -> str:
        return sentence_to_name(re.sub(I_REGEX, '', self.text))

    @property
    def inputs(self) -> list[str]:
        return re.findall(I_REGEX, self.text)

    @property
    def param_names(self) -> list[str]:
        return re.findall(PARAM_REGEX, self.text)

    @property
    def output_names(self) -> tuple[str, ...]:
        return tuple(sentence_to_name(s) for s in re.findall(O_REGEX, self.text))


class ScenarioSpec(stock.Repr, stock.Hashable):
    def __init__(self, title: str, doc_lines: list[str]):
        self.title = title
        self.doc_lines = doc_lines
        self.steps: tuple[StepSpec, ...] = tuple(StepSpec.generate_steps(self.doc_lines))
        self.is_test: bool = True

    def __str__(self) -> str:
        is_test = 't' if self.is_test else 'd'
        return '\n'.join([f'({is_test}) {self.name}', indent(self.steps_text)])

    def eqkey(self) -> tuple[str, bool, tuple[StepSpec, ...]]:
        return self.name, self.is_test, self.steps

    @property
    def name(self) -> str:
        return sentence_to_name(self.title)

    @property
    def steps_text(self) -> str:
        return '\n'.join([repr(s) for s in self.steps])


class FeatureClassSpec(stock.Repr):
    def __init__(self, class_name: str, scenarios: list[dict], doc: str = '',
                 bases=None, mro_bases=None, inherited: bool = False):
        self.class_name = class_name
        self.doc = doc
        self.bases = bases or set()
        self.mro_bases = mro_bases or set()
        self.inherited = inherited
        self.scenarios: dict[str, ScenarioSpec] = {
            sentence_to_name(s['title']): ScenarioSpec(**s) for s in scenarios}

    def __str__(self) -> str:
        head = f'{self.class_name}: ' + ', '.join([f'{key}={getattr(self, key)}' for key in [
            'bases', 'mro_bases', 'inherited']])

        return '\n'.join([head, indent(indent(self.doc)), indent(self.scenarios_text)])

    @property
    def test_class_name(self) -> str:
        return f'Test{self.class_name}' if self.is_test else self.class_name

    @property
    def is_test(self) -> bool:
        return not self.inherited

    @property
    def scenarios_text(self) -> str:
        return '\n'.join([repr(s) for s in self.scenarios.values()])

    @property
    def steps(self) -> dict[str, StepSpec]:
        return {s.name: s for s in itertools.chain(*(sc.steps for sc in self.scenarios.values()))}


class FeaturesSpec(stock.Repr):
    @classmethod
    def from_specs_dir(cls, specs_path: str) -> FeaturesSpec:
        """
        Constructs feature class specifications to be employed by the coders.
        Raises `FeaturesSpecError` for detected inconsistencies
        """
        duplicate_errors = []
        prepared_specs = list(cls.yield_prepared_specs(specs_path))
        duplicate_errors.append(cls.check_if_duplicate_class_names(
            f.class_name for f in prepared_specs))
        duplicate_errors.append(cls.check_if_duplicate_scenarios(prepared_specs))
        duplicate_errors = list(filter(None, duplicate_errors))

        if duplicate_errors:
            raise exceptions.FeaturesSpecError('\n'.join(duplicate_errors))

        return cls(cls.sets_to_lists(cls.localize_steps(cls.sort(cls.simplify_bases(
            cls.check_if_cyclical_inheritance(cls.set_mro_bases(
                cls.prepare_inheritance_specs({f.class_name: f for f in prepared_specs}))))))))

    def __init__(self, features: dict[str, FeatureClassSpec]):
        self.features = features

    def __str__(self) -> str:
        return '\n'.join([self.class_bases_text, indent(self.features_text)])

    @property
    def scenarios(self) -> dict[str, str]:
        return self.get_scenarios(self.features)

    @property
    def class_bases(self) -> list[tuple[str, set]]:
        return list(map(lambda it: (it[0], set(it[1].bases)), self.features.items()))

    @property
    def class_bases_text(self) -> str:
        return pprint.pformat(list(map(lambda it: make_class_head(*it), self.class_bases)),
                              indent=2, width=180)

    @property
    def features_text(self) -> str:
        return '\n'.join([repr(f) for f in self.features.values()])

    @staticmethod
    def sets_to_lists(features: dict[str, FeatureClassSpec]) -> dict[str, FeatureClassSpec]:
        for feature_spec in features.values():
            feature_spec.bases = sorted(feature_spec.bases)
            feature_spec.mro_bases = sorted(feature_spec.mro_bases)

        return features

    @classmethod
    def prepare_inheritance_specs(cls, features: dict[str, FeatureClassSpec]) -> dict[str, FeatureClassSpec]:
        for spec in features.values():
            other_scenario_names = cls.get_scenarios(features, spec.class_name)

            for step in spec.steps.values():
                if step.name in other_scenario_names:
                    other_class_name = other_scenario_names[step.name]
                    spec.mro_bases.add(other_class_name)
                    spec.bases.add(other_class_name)
                    features[other_class_name].scenarios[step.name].is_test = False
                    features[other_class_name].inherited = True
                    step.is_scenario = True
                elif step.name in spec.scenarios:
                    step.is_scenario = True
                    spec.scenarios[step.name].is_test = False

        return features

    @staticmethod
    def localize_steps(features: dict[str, FeatureClassSpec]) -> dict[str, FeatureClassSpec]:
        for spec in features.values():
            for step in spec.steps.values():
                for base_class in spec.mro_bases:
                    if step.name in features[base_class].steps:
                        step.is_local = False

        return features

    @classmethod
    def yield_prepared_specs(cls, specs_path: str) -> Iterator[FeatureClassSpec]:
        for story_yml_name in os.listdir(specs_path):
            with open(os.path.join(specs_path, story_yml_name)) as feature_yml:
                yml_feature = yaml.load(feature_yml.read(), Loader=yaml.FullLoader)

            yield FeatureClassSpec(
                class_name=cls.title_to_class_name(yml_feature.pop('Title')),
                doc=yml_feature.pop('Story').strip(),
                scenarios=[dict(title=title, doc_lines=lines)
                           for title, lines in yml_feature.pop('Scenarios').items()])

    @staticmethod
    def simplify_bases(features: dict[str, FeatureClassSpec]) -> dict[str, FeatureClassSpec]:
        for spec in filter(lambda f: len(f.bases) > 1, features.values()):
            bases = set(spec.bases)

            for base_name in spec.bases:
                bases -= bases & features[base_name].bases

            spec.bases = bases

        return features

    @staticmethod
    def check_if_cyclical_inheritance(features: dict[str, FeatureClassSpec]) -> dict[str, FeatureClassSpec]:
        for class_name, feature_spec in features.items():
            for base_class_name in feature_spec.mro_bases:
                if class_name in features[base_class_name].mro_bases:
                    raise exceptions.FeaturesSpecError(
                        'Cyclical inheritance between {0} and {1}'.format(*sorted([
                            class_name, base_class_name])))

        return features

    @staticmethod
    def sort(features: dict[str, FeatureClassSpec]) -> OrderedDict[str, FeatureClassSpec]:
        """
        Sort (or try to sort) the features so that tester classes can be
        consistently defined.

        `MAX_INHERITANCE_LEVEL` is a limit for debugging, to prevent an
        infinite loop here, which should be forbidden by previous validation
        in the constructor
        """
        bases = {class_name: {
            'bases': spec.bases, 'ordinal': 0 if not spec.bases else 1}
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

        return OrderedDict(sorted(
            features.items(), key=lambda it: bases[it[0]]['ordinal']))

    @staticmethod
    def set_mro_bases(features: dict[str, FeatureClassSpec]) -> dict[str, FeatureClassSpec]:
        for name, spec in features.items():
            spec.mro_bases.update(*(features[cn].bases for cn in spec.bases))
            spec.mro_bases.discard(name)

        return features

    @staticmethod
    def check_if_duplicate_class_names(names: Iterable[str]) -> Optional[str]:
        repeated = list(map(lambda it: it[0], filter(lambda it: it[1] > 1, Counter(names).items())))

        if repeated:
            return f'Duplicate titles are not supported, {repeated}'

        return None

    @staticmethod
    def check_if_duplicate_scenarios(prepared_specs: list[FeatureClassSpec]) -> Optional[str]:
        scenarios = list(itertools.chain(*(
            [(nm, spec.class_name) for nm in spec.scenarios]
            for spec in prepared_specs)))
        repeated = dict(map(
            lambda it: (it[0], [cn for nm, cn in scenarios if nm == it[0]]),
            filter(lambda it: it[1] > 1, Counter([nm for nm, cn in scenarios]).items())))

        if repeated:
            return f'Repeated scenario names are not supported, {repeated}'

        return None

    @staticmethod
    def get_scenarios(features: dict[str, FeatureClassSpec], *exclude: str) -> dict[str, str]:
        return {name: class_name for name, class_name in itertools.chain(*(
            [(nm, cn) for nm in spec.scenarios]
            for cn, spec in features.items() if cn not in exclude))}

    @staticmethod
    def title_to_class_name(title: str) -> str:
        return ''.join(map(str.capitalize, title.split()))
