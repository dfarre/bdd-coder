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
        with open(os.path.join(self.specs_path, 'repr.txt')) as repr_file:
            assert repr(self.specs) == repr_file.read().strip()

    def test_inheritance__cyclical_error(self):
        from_path, to_path = (os.path.join(self.specs_path, 'forbidden-story.yml'),
                              os.path.join(self.specs_path, 'features/forbidden-story.yml'))
        shutil.move(from_path, to_path)

        self.assertRaisesRegex(
            exceptions.FeaturesSpecError,
            r'^Cyclical inheritance between [a-zA-Z]+ and [a-zA-Z]+$',
            features.FeaturesSpec.from_specs_dir, self.specs_path)

        shutil.move(to_path, from_path)

    def test_inheritance__self_reference(self):
        assert self.specs.features['FakeOne']['scenarios']['ones_first_scenario'][
            'inherited'] is True
        assert self.specs.features['FakeOne']['scenarios']['ones_second_scenario'][
            'steps'][0].own is False
        assert self.specs.features['FakeOne']['inherited'] is False
        assert self.specs.features['FakeTwo']['inherited'] is True
        assert self.specs.features['FakeThree']['inherited'] is True

    def test_inheritance__no_redundant_bases(self):
        assert self.specs.class_bases == [
            ('FakeThree', set()), ('FakeTwo', {'FakeThree'}), ('FakeOne', {'FakeTwo'})]

    def test_reference_to_alias_yields_base_method(self):
        assert self.specs.base_methods == ['something_cool']
        assert self.specs.features['FakeOne']['scenarios']['ones_first_scenario'][
            'steps'][0].own is False
