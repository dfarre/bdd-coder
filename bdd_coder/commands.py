import argparse
import importlib
import inspect
import os
import subprocess
import sys

from bdd_coder import LOGS_DIR_NAME
from bdd_coder import SUCCESS_MSG
from bdd_coder.coder import coders
from bdd_coder.tester import tester


class Command:
    arguments = ()

    def __init__(self):
        self.parser = argparse.ArgumentParser()

        for args, kwargs in self.arguments:
            self.parser.add_argument(*args, **kwargs)


class MakeBlueprint(Command):
    arguments = (
        (('--base-class', '-c'), dict(help='default: unittest.TestCase')),
        (('--specs-path', '-i'), dict(help='default: behaviour/specs')),
        (('--tests-path', '-o'), dict(help='default: next to specs')),
        (('--tests-module-name', '-n'), dict(help='default: stories (test_stories.py)')),
        (('--pytest',), dict(action='store_true', help='run pytest on the blueprint')))

    def __call__(self):
        kwargs = {k: v for k, v in self.parser.parse_args()._get_kwargs() if v is not None}
        test = kwargs.pop('pytest')

        coder = coders.PackageCoder(**kwargs)
        coder.create_tester_package()

        if test:
            subprocess.check_output(['pytest', '-vv', coder.tests_path])


class CheckPendingScenarios(Command):
    arguments = ((('logs_parent',), {}),)

    def __call__(self, logs_parent=''):
        logs_dir = os.path.join(logs_parent or self.parser.parse_args().logs_parent,
                                LOGS_DIR_NAME)

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
        return 0


class MakeYamlSpecs(Command):
    arguments = ((('test_module',), dict(help='passed to `importlib.import_module`')),
                 (('specs_path',), dict(help='will try to write the YAML files in here')),
                 (('--overwrite', '-w'), dict(action='store_true')))

    def __call__(self):
        args = self.parser.parse_args()
        os.makedirs(args.specs_path, exist_ok=args.overwrite)
        features_path = os.path.join(args.specs_path, 'features')
        os.makedirs(features_path, exist_ok=args.overwrite)
        testers = [v for k, v in inspect.getmembers(importlib.import_module(args.test_module))
                   if inspect.isclass(v) and issubclass(v, tester.BddTester)]

        steps = {cls.steps for cls in testers}.pop()
        tester.YamlDumper.dump_yaml_aliases(
            steps.aliases, os.path.join(args.specs_path, 'aliases.yml'))

        for cls in testers:
            cls.dump_yaml_feature(os.path.join(features_path, f'{cls.__name__.lower()}.yml'))


make_blueprint = MakeBlueprint()
check_pending_scenarios = CheckPendingScenarios()
make_yaml_specs = MakeYamlSpecs()
