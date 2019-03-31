import collections
import os
import shutil
import unittest
import unittest.mock as mock

from bdd_coder import commands
from bdd_coder import LOGS_DIR_NAME, FAIL, OK, COMPLETION_MSG

from example.tests import base
from example.tests import test_stories


class ValidateBasesTests(unittest.TestCase):
    specs = collections.namedtuple('FakeSpecs', ('class_bases', 'features'))

    def assert_error(self, value):
        assert base.BddTester.validate_bases(self.specs) == value

    def test_wrong_name(self):
        self.specs.class_bases = [('FooStory', set())]

        self.assert_error('NewGame != FooStory')

    def init_specs(self):
        self.specs.class_bases = [('NewGame', set()), ('ClearBoard', set())]
        self.specs.features = collections.OrderedDict([
            ('NewGame', {'inherited': True}), ('ClearBoard', {'inherited': False})])

    def test_wrong_bases(self):
        self.init_specs()

        self.assert_error("Bases {'NewGame'} defined in ClearBoard do not "
                          f'match the specified ones set()')

    def test_missing_test_case(self):
        self.init_specs()
        self.specs.features['NewGame']['inherited'] = False

        self.assert_error('Expected one BaseTestCase subclass in NewGame')

    def test_unexpected_test_case(self):
        self.init_specs()
        self.specs.features['ClearBoard']['inherited'] = True

        self.assert_error('Unexpected BaseTestCase subclass in ClearBoard')


class MakeYamlSpecsTests(unittest.TestCase):
    specs_path = 'tmp'
    command = commands.MakeYamlSpecs(test_mode=True)
    files_made_msg = f'Specification files generated in {specs_path}\n'

    def setUp(self):
        os.makedirs(self.specs_path)
        self.features_dir = os.path.join(self.specs_path, 'features')

    def tearDown(self):
        shutil.rmtree(self.specs_path)

    def call(self, **kwargs):
        return self.command(
            test_module=test_stories, specs_path=self.specs_path, **kwargs)

    def test_raises_cannot_overwrite(self):
        self.assertRaises(OSError, self.call)

    @mock.patch('sys.stdout.write')
    @mock.patch('example.tests.test_stories.ClearBoard.dump_yaml_feature')
    @mock.patch('example.tests.test_stories.NewGame.dump_yaml_feature')
    @mock.patch('bdd_coder.tester.tester.YamlDumper.dump_yaml_aliases')
    def test__no_validation(self, dump_aliases_mock, dump_game_mock, dump_board_mock,
                            stdout_mock):
        os.makedirs(self.features_dir)

        assert self.call(overwrite=True, validate=False) == 0
        dump_aliases_mock.assert_called_once_with(base.steps.aliases, self.specs_path)
        dump_game_mock.assert_called_once_with(self.features_dir)
        dump_board_mock.assert_called_once_with(self.features_dir)
        stdout_mock.assert_called_once_with(self.files_made_msg)

    @mock.patch('sys.stdout.write')
    def test__validated_ok(self, stdout_mock):
        os.makedirs(self.features_dir)

        assert self.call(overwrite=True, validate=True) == 0
        assert stdout_mock.call_args_list == list(map(
            mock.call, (self.files_made_msg, 'And validated\n')))

    @mock.patch('sys.stderr.write')
    def test__features_spec_error(self, stderr_mock):
        os.makedirs(self.features_dir)
        doc_ok = test_stories.NewGame.test_odd_boards.__doc__
        test_stories.NewGame.test_odd_boards.__doc__ = doc_ok + 'And start board'

        assert self.call(overwrite=True, validate=True) == 1
        stderr_mock.assert_called_once_with(
            'Cyclical inheritance between NewGame and ClearBoard\n')

        test_stories.NewGame.test_odd_boards.__doc__ = doc_ok

    @mock.patch('bdd_coder.tester.tester.BddTester.validate_bases', return_value='Error!')
    @mock.patch('sys.stderr.write')
    def test__class_bases_error(self, stderr_mock, validate_bases_mock):
        os.makedirs(self.features_dir)

        assert self.call(overwrite=True, validate=True) == 1
        stderr_mock.assert_called_once_with(
            "Expected class structure ['class NewGame', 'class ClearBoard(NewGame)'] "
            'from docs does not match the defined one. Error!\n')


SPECS_ERROR = ("Duplicate titles are not supported, ['FakeFoo']\n"
               'Repeated scenario names are not supported, '
               "{'scen_one': ['FakeFoo', 'FakeFoo']}\n")


class MakeBlueprintTests(unittest.TestCase):
    command = commands.MakeBlueprint(test_mode=True)

    @mock.patch('bdd_coder.coder.coders.PackageCoder.__init__', return_value=None)
    @mock.patch('bdd_coder.coder.coders.PackageCoder.create_tester_package',
                return_value='Output')
    def test_create_package_call(self, create_package_mock, PackageCoderMock):
        kwargs = {'foo': None, 'bar': 100, 'qux': 'hello'}
        assert self.command(**kwargs) == 0
        kwargs.pop('foo')
        PackageCoderMock.assert_called_once_with(**kwargs)
        create_package_mock.assert_called_once_with()

    @mock.patch('sys.stderr.write')
    def test_inconsistent_specs(self, stderr_mock):
        assert self.command(specs_path='tests/specs_wrong') == 1
        stderr_mock.assert_called_once_with(SPECS_ERROR)


class PatchBlueprintTests(unittest.TestCase):
    command = commands.PatchBlueprint(test_mode=True)

    @mock.patch('bdd_coder.coder.coders.PackagePatcher.__init__', return_value=None)
    @mock.patch('bdd_coder.coder.coders.PackagePatcher.patch',
                return_value='Output')
    def test_patch_package_call(self, patch_package_mock, PackagePatcherMock):
        kwargs = {'foo': None, 'bar': 100, 'qux': 'hello'}
        assert self.command(**kwargs) == 0
        kwargs.pop('foo')
        PackagePatcherMock.assert_called_once_with(**kwargs)
        patch_package_mock.assert_called_once_with()

    @mock.patch('sys.stderr.write')
    def test_inconsistent_specs(self, stderr_mock):
        assert self.command(
            specs_path='tests/specs_wrong', test_module='example.tests.test_stories'
        ) == 1
        stderr_mock.assert_called_once_with(SPECS_ERROR)


SUCCESS_MSG = f'{COMPLETION_MSG} ▌ 3 {OK}'


class CheckPendingScenariosTests(unittest.TestCase):
    command = commands.CheckPendingScenarios(test_mode=True)

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

    @mock.patch('sys.stdout.write')
    def assert_when_no_logs(self, stdout_mock):
        assert self.command(logs_parent=self.tmp_dir) == 2
        stdout_mock.assert_called_once_with('No logs found\n')

    def test_no_logs_dir(self):
        self.assert_when_no_logs()

    def test_no_log_files(self):
        os.makedirs(os.path.join(self.tmp_dir, LOGS_DIR_NAME))
        self.assert_when_no_logs()

    @mock.patch('sys.stderr.write')
    def test_no_success(self, stderr_mock):
        self.make_fake_logs()

        assert self.command(logs_parent=self.tmp_dir) == 1
        stderr_mock.assert_called_once_with(
            f'{FAIL} Some scenarios did not run! Check the logs in {self.logs_dir}\n')

    @mock.patch('sys.stdout.write')
    def test_success(self, stdout_mock):
        self.make_fake_logs()

        with open(os.path.join(self.logs_dir, '2019-03-02.log'), 'w') as log02:
            log02.write(SUCCESS_MSG + '\n\n')

        assert self.command(logs_parent=self.tmp_dir) == 0
        stdout_mock.assert_called_once_with(SUCCESS_MSG + '\n')
