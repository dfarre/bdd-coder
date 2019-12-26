import collections
import os
import shutil
import subprocess
import unittest
import unittest.mock as mock

from bdd_coder import LOGS_DIR_NAME, FAIL, OK, COMPLETION_MSG

from bdd_coder.exceptions import InconsistentClassStructure

from example.tests import base
from example.tests import test_stories


class CommandsE2ETestCase(unittest.TestCase):
    command_name = ''

    def call(self, *args):
        return subprocess.run((self.command_name,) + args,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE)


class ValidateBasesTests(unittest.TestCase):
    fake_specs = collections.namedtuple('FakeSpecs', ('class_bases', 'features'))
    fake_specs.get_class_bases_text = lambda: ['class NewGame', 'class ClearBoard(NewGame)']

    def init_specs(self):
        self.fake_specs.class_bases = [('NewGame', set()), ('ClearBoard', set())]
        self.fake_specs.features = collections.OrderedDict([
            ('NewGame', {'inherited': True}), ('ClearBoard', {'inherited': False})])
        self.wrong_bases_error = ("Bases {'NewGame'} declared in ClearBoard do not "
                                  'match the specified ones set()')

    def assert_error(self, error):
        with self.assertRaises(InconsistentClassStructure) as contextm:
            base.BddTester.validate_bases(self.fake_specs)

        assert str(contextm.exception) == (
            f'Expected class structure from docs does not match the defined one: {error}')

    def test_wrong_bases(self):
        self.init_specs()

        self.assert_error(self.wrong_bases_error)

    def test_missing_test_case(self):
        self.init_specs()
        self.fake_specs.features['NewGame']['inherited'] = False

        self.assert_error('Expected one BaseTestCase subclass in NewGame. '
                          + self.wrong_bases_error)

    def test_unexpected_test_case(self):
        self.init_specs()
        self.fake_specs.features['ClearBoard']['inherited'] = True

        self.assert_error('Unexpected BaseTestCase subclass in ClearBoard. '
                          + self.wrong_bases_error)

    def test_sets_differ(self):
        self.fake_specs.class_bases = [('FooStory', set())]

        self.assert_error('Sets of class names differ: <SetPair: doc ⪥ code: '
                          "{'FooStory'} | ø | {'ClearBoard', 'NewGame'}>")


class MakeYamlSpecsTests(CommandsE2ETestCase):
    specs_path = 'tmp'
    command_name = 'bdd-make-yaml-specs'
    files_made_msg = f'Specification files generated in {specs_path}\n'

    def setUp(self):
        os.makedirs(self.specs_path)
        self.features_dir = os.path.join(self.specs_path, 'features')

    def tearDown(self):
        shutil.rmtree(self.specs_path)

    def call(self, suff='', overwrite=False):
        pref = 'wrong_' if suff else ''
        args = [f'example.{pref}tests.test_stories{suff}', self.specs_path] + (
            ['--overwrite'] if overwrite else [])

        return super().call(*args)

    def test_overwrite_error(self):
        process = self.call(overwrite=False)

        assert process.returncode == 4
        assert process.stderr.decode() == (
            "OverwriteError: Cannot overwrite tmp (--overwrite not set). "
            "[Errno 17] File exists: 'tmp'\n")
        assert process.stdout.decode() == ''

    def test_validated_ok(self):
        os.makedirs(self.features_dir)
        process = self.call(overwrite=True)

        assert process.returncode == 0
        assert process.stdout.decode() == (
            self.files_made_msg + 'Test case hierarchy validated\n')
        assert process.stderr.decode() == ''

    def test_features_spec_error(self):
        os.makedirs(self.features_dir)
        process = self.call('_cyclical', overwrite=True)

        assert process.returncode == 5
        assert process.stderr.decode() == (
            'FeaturesSpecError: Cyclical inheritance between NewGame and ClearBoard\n')
        assert process.stdout.decode() == 'Specification files generated in tmp\n'

    def test_class_bases_error(self):
        os.makedirs(self.features_dir)
        process = self.call('_not_inherited', overwrite=True)

        assert process.returncode == 6
        assert process.stderr.decode() == (
            'InconsistentClassStructure: Expected class structure from docs does not '
            'match the defined one: Expected one BaseTestCase subclass in NewGame\n')


SPECS_ERROR = ("FeaturesSpecError: Duplicate titles are not supported, ['FakeFoo']\n"
               'Repeated scenario names are not supported, '
               "{'scen_one': ['FakeFoo', 'FakeFoo']}\n")


class MakeBlueprintTests(CommandsE2ETestCase):
    command_name = 'bdd-blueprint'

    def test_create_package_call(self):
        process = self.call('--specs-path', 'example/specs', '--overwrite')

        assert process.returncode == 0

    def test_inconsistent_specs(self):
        process = self.call('--specs-path', 'tests/specs_wrong')

        assert process.returncode == 4
        assert process.stderr.decode() == SPECS_ERROR
        assert process.stdout.decode() == ''


class PatchBlueprintTests(CommandsE2ETestCase):
    command_name = 'bdd-patch'

    def test_patch_package_call(self):
        process = self.call('example.tests.test_stories', 'example/specs')

        assert process.returncode == 0

    def test_inconsistent_specs(self):
        process = self.call('example.tests.test_stories', 'tests/specs_wrong')

        assert process.returncode == 4
        assert process.stdout.decode() == 'Specification files generated in .tmp-specs\n'
        assert process.stderr.decode() == SPECS_ERROR


SUCCESS_MSG = f'{COMPLETION_MSG} ▌ 3 {OK}'


class CheckPendingScenariosTests(CommandsE2ETestCase):
    command_name = 'bdd-pending-scenarios'

    def setUp(self):
        self.tmp_dir = 'tmp'
        os.makedirs(self.tmp_dir)
        self.logs_dir = os.path.join(self.tmp_dir, LOGS_DIR_NAME)

    def tearDown(self):
        shutil.rmtree(self.tmp_dir)

    def make_fake_logs(self):
        os.makedirs(self.logs_dir)

        with open(os.path.join(self.logs_dir, '2019-03-01.log'), 'w') as log01, \
                open(os.path.join(self.logs_dir, '2019-03-02.log'), 'w') as log02:
            log01.write(SUCCESS_MSG + '\n\n')
            log02.write('Foo OK\n\n')

    def assert_when_no_logs(self):
        process = self.call(self.tmp_dir)

        assert process.returncode == 4
        assert process.stdout.decode() == ''
        assert process.stderr.decode() == (
            'LogsNotFoundError: No logs found in tmp/.bdd-run-logs\n')

    def test_no_logs_dir(self):
        self.assert_when_no_logs()

    def test_no_log_files(self):
        os.makedirs(os.path.join(self.tmp_dir, LOGS_DIR_NAME))
        self.assert_when_no_logs()

    def test_no_success(self):
        self.make_fake_logs()
        process = self.call(self.tmp_dir)

        assert process.returncode == 3
        assert process.stdout.decode() == ''
        assert process.stderr.decode() == (
            'PendingScenariosError: Some scenarios did not run! '
            f'Check the logs in {self.logs_dir}\n')

    def test_success(self):
        self.make_fake_logs()

        with open(os.path.join(self.logs_dir, '2019-03-02.log'), 'w') as log02:
            log02.write(SUCCESS_MSG + '\n\n')

        process = self.call(self.tmp_dir)

        assert process.returncode == 0
        assert process.stdout.decode() == SUCCESS_MSG + '\n'
        assert process.stderr.decode() == ''
