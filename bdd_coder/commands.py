import abc
import argparse
import importlib
import inspect
import os
import sys

from bdd_coder import LOGS_DIR_NAME
from bdd_coder import SUCCESS_MSG
from bdd_coder.coder import coders
from bdd_coder.coder import features
from bdd_coder.tester import tester


class Command(metaclass=abc.ABCMeta):
    arguments = ()

    def __init__(self, test_mode=False):
        if not test_mode:
            self.parser = argparse.ArgumentParser()

            for args, kwargs in self.arguments:
                self.parser.add_argument(*args, **kwargs)

        self.test_mode = test_mode

    def __call__(self, **kwargs):
        items = kwargs.items() if self.test_mode else self.parser.parse_args()._get_kwargs()

        return self.call(**{key: value for key, value in items if value is not None})

    @abc.abstractmethod
    def call(self, **kwargs):
        """The command function"""


class MakeBlueprint(Command):
    arguments = (
        (('--base-class', '-c'), dict(help='default: unittest.TestCase')),
        (('--specs-path', '-i'), dict(help='default: behaviour/specs')),
        (('--tests-path', '-o'), dict(help='default: next to specs')),
        (('--tests-module-name', '-n'), dict(help='default: stories (test_stories.py)')))

    def call(self, **kwargs):
        try:
            coder = coders.PackageCoder(**kwargs)
        except features.FeatureSpecsError as error:
            sys.stderr.write(str(error) + '\n')
            return 1

        sys.stdout.write(coder.create_tester_package())
        return 0


class CheckPendingScenarios(Command):
    arguments = ((('logs_parent',), {}),)

    def call(self, **kwargs):
        logs_dir = os.path.join(kwargs['logs_parent'], LOGS_DIR_NAME)

        if os.path.isdir(logs_dir):
            log_names = sorted(os.listdir(logs_dir))

            if log_names:
                with open(os.path.join(logs_dir, log_names[-1]), 'rb') as log_bytes:
                    log_bytes.seek(-5, 2)

                    if log_bytes.read().decode()[0] == '✅':
                        sys.stdout.write(SUCCESS_MSG + '\n')
                        return 0
                    else:
                        sys.stderr.write(
                            f'✘ Some scenarios did not run! Check the logs in {logs_dir}\n')
                        return 1

        sys.stdout.write('No logs found\n')
        return 2


class MakeYamlSpecs(Command):
    arguments = ((('test_module',), dict(help='passed to `importlib.import_module`')),
                 (('specs_path',), dict(help='will try to write the YAML files in here')),
                 (('--overwrite', '-w'), dict(action='store_true')),
                 (('--validate', '-v'), dict(action='store_true')),)

    def call(self, overwrite=False, **kwargs):
        os.makedirs(kwargs['specs_path'], exist_ok=overwrite)
        features_path = os.path.join(kwargs['specs_path'], 'features')
        os.makedirs(features_path, exist_ok=overwrite)
        module = (kwargs['test_module'] if self.test_mode else
                  importlib.import_module(kwargs['test_module']))
        testers = [obj for name, obj in inspect.getmembers(module)
                   if inspect.isclass(obj) and issubclass(obj, tester.BddTester)]

        steps = {cls.steps for cls in testers}.pop()
        tester.YamlDumper.dump_yaml_aliases(steps.aliases, kwargs['specs_path'])

        for cls in testers:
            cls.dump_yaml_feature(features_path)

        sys.stdout.write(f"Specification files generated in {kwargs['specs_path']}\n")

        if kwargs['validate']:
            try:
                features.FeaturesSpec(kwargs['specs_path'])
            except features.FeatureSpecsError as error:
                sys.stderr.write(str(error) + '\n')
                return 1
            else:
                sys.stdout.write('And validated\n')

        return 0


make_blueprint = MakeBlueprint()
check_pending_scenarios = CheckPendingScenarios()
make_yaml_specs = MakeYamlSpecs()
