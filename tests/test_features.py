import os
import shutil
import unittest

from bdd_coder import exceptions
from bdd_coder import features


class FeaturesSpecTests(unittest.TestCase):
    def setUp(self):
        self.specs_path = 'tests/specs_ok'
        self.specs = features.FeaturesSpec.from_specs_dir(self.specs_path)

    def test_str(self):
        with open(os.path.join(os.path.dirname(self.specs_path), 'specs_ok_repr.txt')
                  ) as repr_file:
            assert repr(self.specs) == repr_file.read().strip()

    def test_inheritance__self_reference(self):
        assert self.specs.features['FakeOne'].scenarios[
            'ones_second_scenario'].steps[0].is_local is True
        assert self.specs.features['FakeOne'].inherited is False
        assert self.specs.features['FakeTwo'].inherited is True
        assert self.specs.features['FakeThree'].inherited is True

    def test_inheritance__no_redundant_bases(self):
        assert self.specs.class_bases == [
            ('FakeThree', set()), ('FakeTwo', {'FakeThree'}), ('FakeOne', {'FakeTwo'})]


class FeaturesSpecCyclicalErrorTests(unittest.TestCase):
    def setUp(self):
        self.specs_path = 'tests/specs_ok'
        self.specs = features.FeaturesSpec.from_specs_dir(self.specs_path)
        self.from_path, self.to_path = (
            os.path.join(os.path.dirname(self.specs_path), 'forbidden-story.yml'),
            os.path.join(self.specs_path, 'forbidden-story.yml'))
        shutil.move(self.from_path, self.to_path)

    def tearDown(self):
        shutil.move(self.to_path, self.from_path)

    def test_inheritance__cyclical_error(self):
        self.assertRaisesRegex(
            exceptions.FeaturesSpecError,
            r'^Cyclical inheritance between [a-zA-Z]+ and [a-zA-Z]+$',
            features.FeaturesSpec.from_specs_dir, self.specs_path)


class StepSpecTests(unittest.TestCase):
    def test_input_gegex(self):
        step_spec = features.StepSpec('Given IPv6 $(::) and IPv4 $(1.2.3.4,0.0.0.0)', 0)
        assert step_spec.name == 'ipv6_and_ipv4'

    def test_repeated_parameter_names(self):
        self.assertRaisesRegex(
            exceptions.FeaturesSpecError,
            r'^Repeated parameter names in \(\+\) param_and_param \[param, param\] ↦ \(\)$',
            features.StepSpec, 'Given $param and $param', 0)
