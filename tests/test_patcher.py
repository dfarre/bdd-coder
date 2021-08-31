import shutil
import unittest

from bdd_coder import coders, text_utils


class AdvancedPatcherTests(unittest.TestCase):
    initial_module_dir = 'example/advanced_tests'
    tmp_dir = 'example/tmp'
    module_to_patch = 'example.tmp.test_stories'

    def setUp(self):
        shutil.copytree(self.initial_module_dir, self.tmp_dir)

    def tearDown(self):
        shutil.rmtree(self.tmp_dir)

    def patch(self, new_specs_dir):
        coders.PackagePatcher(
            test_module=self.module_to_patch, specs_path=new_specs_dir
        ).patch(run_pytest=False)

    def test_no_changes(self):
        self.patch('example/advanced_specs')
        text_utils.assert_test_files_match('example/advanced_tests', 'example/tmp')

    def test_patch_from_tests(self):
        specs_path = 'example/new_advanced_specs'
        base_tester, _ = coders.get_base_tester('example.new_advanced_tests.test_stories')
        features_spec = base_tester.features_spec(specs_path)
        base_tester.validate_bases(features_spec)
        self.patch(specs_path)
        text_utils.assert_test_files_match('example/new_advanced_tests', 'example/tmp')
