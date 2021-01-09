import os
import shutil
import unittest
import yaml

from example.tests import aliases
from example.tests import test_stories

from bdd_coder.tester import tester


class YamlDumpTests(unittest.TestCase):
    def setUp(self):
        os.makedirs('tmp')

    def tearDown(self):
        shutil.rmtree('tmp')

    def assert_equal_yamls(self, lpath, rpath):
        with open(lpath) as lfile, open(rpath) as rfile:
            assert yaml.load(lfile.read(), Loader=yaml.FullLoader) == yaml.load(
                rfile.read(), Loader=yaml.FullLoader)

    def test_aliases_yaml(self):
        tester.YamlDumper.dump_yaml_aliases(aliases.MAP, 'tmp')

        self.assert_equal_yamls('tmp/aliases.yml', 'example/specs/aliases.yml')

    def test_feature_yamls__newgame(self):
        test_stories.NewGame.dump_yaml_feature('tmp')

        self.assert_equal_yamls(
            'tmp/new-game.yml', 'example/specs/features/new-game.yml')

    def test_feature_yamls__clearboard(self):
        test_stories.TestClearBoard.dump_yaml_feature('tmp')

        self.assert_equal_yamls(
            'tmp/clear-board.yml', 'example/specs/features/clear-board.yml')
