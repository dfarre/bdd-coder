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
            assert yaml.load(lfile.read()) == yaml.load(rfile.read())

    def test_aliases_yml(self):
        tester.YamlDumper.dump_yaml_aliases(aliases.MAP, 'tmp/aliases.yml')

        self.assert_equal_yamls('tmp/aliases.yml', 'example/specs/aliases.yml')

    def test_feature_yamls__newgame(self):
        test_stories.NewGame.dump_yaml_feature('tmp/newgame.yml')

        self.assert_equal_yamls('tmp/newgame.yml', 'example/specs/features/new-game.yml')

    def test_feature_yamls__clearboard(self):
        test_stories.ClearBoard.dump_yaml_feature('tmp/clearboard.yml')

        self.assert_equal_yamls('tmp/clearboard.yml', 'example/specs/features/clear-board.yml')
