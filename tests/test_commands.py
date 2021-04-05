import collections
import os
import shutil
import subprocess
import unittest

from bdd_coder import OK, COMPLETION_MSG

from bdd_coder.exceptions import InconsistentClassStructure

from example.tests import base


class CommandsE2ETestCase(unittest.TestCase):
    command_name = ''

    def assert_call(self, *args, exit=0, stdout=None, stderr=None):
        process = subprocess.run((self.command_name,) + args,
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        assert process.returncode == exit, \
            f'returned {process.returncode}:\nStdout: {process.stdout.decode()}\n' \
            f'Stderr: {process.stderr.decode()}'

        if stdout:
            assert process.stdout.decode() == stdout

        if stderr:
            assert process.stderr.decode() == stderr


class ValidateBasesTests(unittest.TestCase):
    fake_specs = collections.namedtuple('FakeSpecs', ('class_bases', 'features'))

    def setUp(self):
        self.fake_specs.class_bases = [('NewGame', set()), ('ClearBoard', set())]
        self.fake_specs.features = collections.OrderedDict([
            ('NewGame', {'inherited': True}), ('ClearBoard', {'inherited': False})])
        self.wrong_bases_error = ("bases {'NewGame'} declared in ClearBoard do not "
                                  'match the specified ones set()')

    def assert_error(self, error):
        with self.assertRaises(InconsistentClassStructure) as contextm:
            base.BddTester.validate_bases(self.fake_specs)

        assert str(contextm.exception) == (
            f'Expected class structure from docs does not match the defined one: {error}')

    def test_wrong_bases(self):
        self.assert_error(self.wrong_bases_error)

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

    def assert_call(self, suff='', overwrite=False, **kwargs):
        pref = 'wrong_' if suff else ''
        args = [f'example.{pref}tests.test_stories{suff}', self.specs_path] + (
            ['--overwrite'] if overwrite else [])

        return super().assert_call(*args, **kwargs)

    def test_overwrite_error(self):
        self.assert_call(
            overwrite=False, exit=4, stderr="OverwriteError: Cannot overwrite tmp"
            " (--overwrite not set). [Errno 17] File exists: 'tmp'\n", stdout='')

    def test_validated_ok(self):
        os.makedirs(self.features_dir)
        self.assert_call(
            overwrite=True, exit=0, stderr='',
            stdout=self.files_made_msg + 'Test case hierarchy validated\n')

    def test_features_spec_error(self):
        os.makedirs(self.features_dir)
        self.assert_call(
            '_cyclical', overwrite=True, exit=5,
            stderr='FeaturesSpecError: Cyclical inheritance between ClearBoard and NewGame\n',
            stdout='Specification files generated in tmp\n')

    def test_class_bases_error(self):
        os.makedirs(self.features_dir)
        self.assert_call(
            '_not_inherited', overwrite=True, exit=6,
            stderr='InconsistentClassStructure: Expected class structure from docs does not '
            'match the defined one: bases set() declared in ClearBoard do not match '
            "the specified ones {'NewGame'}\n")


SPECS_ERROR = ("FeaturesSpecError: Duplicate titles are not supported, ['FakeFoo']\n"
               'Repeated scenario names are not supported, '
               "{'scen_one': ['FakeFoo', 'FakeFoo']}\n")


class MakeBlueprintTests(CommandsE2ETestCase):
    command_name = 'bdd-blueprint'

    def test_create_package_call(self):
        self.assert_call('--specs-path', 'example/specs', '--overwrite', exit=0)

    def test_inconsistent_specs(self):
        self.assert_call(
            '--specs-path', 'tests/specs_wrong', exit=4, stdout='', stderr=SPECS_ERROR)


class PatchBlueprintTests(CommandsE2ETestCase):
    command_name = 'bdd-patch'

    def test_patch_package_call(self):
        self.assert_call('example.tests.test_stories', 'example/specs', exit=0)

    def test_inconsistent_specs(self):
        self.assert_call(
            'example.tests.test_stories', 'tests/specs_wrong', exit=4,
            stdout='', stderr=SPECS_ERROR)


SUCCESS_MSG = f'{COMPLETION_MSG} ▌ 3 {OK}'


class CheckPendingScenariosTests(CommandsE2ETestCase):
    command_name = 'bdd-pending-scenarios'

    def setUp(self):
        self.tmp_dir = 'tmp'
        os.makedirs(self.tmp_dir)
        self.ok_logs = os.path.join(self.tmp_dir, 'fake_ok_bdd_runs.log')
        self.wrong_logs = os.path.join(self.tmp_dir, 'fake_wrong_bdd_runs.log')

    def tearDown(self):
        shutil.rmtree(self.tmp_dir)

    def make_fake_logs(self):
        with open(self.ok_logs, 'w') as ok_log, open(self.wrong_logs, 'w') as wrong_log:
            ok_log.write(SUCCESS_MSG)
            wrong_log.write('Foo OK\n\n')

    def test_no_log_files(self):
        self.assert_call(
            self.ok_logs, exit=4, stdout='',
            stderr=f'LogsNotFoundError: No logs found in {self.ok_logs}\n')

    def test_no_success(self):
        self.make_fake_logs()
        self.assert_call(
            self.wrong_logs, exit=3, stdout='',
            stderr='PendingScenariosError: Some scenarios did not run! '
            f'Check the logs in {self.wrong_logs}\n')

    def test_success(self):
        self.make_fake_logs()
        self.assert_call(self.ok_logs, exit=0,
                         stdout=f'{COMPLETION_MSG}. Check the logs in {self.ok_logs}\n',
                         stderr='')
