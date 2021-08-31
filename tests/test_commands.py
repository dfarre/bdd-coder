import collections
import os
import shutil
import subprocess
import unittest

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
        self.assert_call(
            overwrite=True, exit=0, stderr='',
            stdout=self.files_made_msg + 'Test case hierarchy validated\n')

    def test_class_bases_error(self):
        self.assert_call(
            '_not_inherited', overwrite=True, exit=6,
            stderr='InconsistentClassStructure: Expected class structure from docs does not '
            'match the defined one: method even_boards not found\n')


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
