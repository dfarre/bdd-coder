import abc
import argparse
import os
import sys

from bdd_coder import LOGS_DIR_NAME
from bdd_coder import OK, FAIL
from bdd_coder.coder import coders
from bdd_coder.coder import features


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


class SpecErrorCommand(Command, metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def try_call(self, **kwargs):
        """May raise `FeaturesSpecError`"""

    def call(self, **kwargs):
        try:
            self.try_call(**kwargs)
            return 0
        except features.FeaturesSpecError as error:
            sys.stderr.write(str(error) + '\n')
            return 1


class MakeBlueprint(SpecErrorCommand):
    params = coders.PackageCoder.get_parameters()
    arguments = (
        ((f'--{params["base_class"].name.replace("_", "-")}', '-c'), dict(
            help=f'default: {params["base_class"].default}')),
        ((f'--{params["specs_path"].name.replace("_", "-")}', '-i'), dict(
            help=f'default: {params["specs_path"].default}')),
        ((f'--{params["tests_path"].name.replace("_", "-")}', '-o'), dict(
            help='default: next to specs')),
        ((f'--{params["test_module_name"].name.replace("_", "-")}', '-n'), dict(
            help=f'Name for test_<name>.py. default: {params["test_module_name"].default}')))

    def try_call(self, **kwargs):
        coders.PackageCoder(**kwargs).create_tester_package()


class PatchBlueprint(SpecErrorCommand):
    params = coders.PackagePatcher.get_parameters()
    arguments = (
        ((params['test_module'].name,), dict(help='passed to `importlib.import_module`')),
        ((params['specs_path'].name,), dict(
            nargs='?', help='Directory to take new specs from. '
            f'default: {coders.PackagePatcher.default_specs_dir_name}/ '
            'next to test package')))

    def try_call(self, **kwargs):
        coders.PackagePatcher(**kwargs).patch()


class CheckPendingScenarios(Command):
    arguments = ((('logs_parent',), {}),)

    def call(self, **kwargs):
        logs_dir = os.path.join(kwargs['logs_parent'], LOGS_DIR_NAME)

        if os.path.isdir(logs_dir):
            log_names = sorted(os.listdir(logs_dir))

            if log_names:
                with open(os.path.join(logs_dir, log_names[-1])) as log:
                    lines = reversed(list(log))
                    next(lines)
                    message = next(lines).strip('\n')

                if message.endswith(OK) or message.endswith(FAIL):
                    sys.stdout.write(message + '\n')
                    return 0
                else:
                    sys.stderr.write(f'{FAIL} Some scenarios did not run! '
                                     f'Check the logs in {logs_dir}\n')
                    return 1

        sys.stdout.write('No logs found\n')
        return 2


class MakeYamlSpecs(Command):
    arguments = ((('test_module',), dict(help='passed to `importlib.import_module`')),
                 (('specs_path',), dict(help='will try to write the YAML files in here')),
                 (('--overwrite', '-w'), dict(action='store_true')),
                 (('--validate', '-v'), dict(action='store_true')),)

    def call(self, overwrite=False, **kwargs):
        base_tester = coders.get_base_tester(kwargs['test_module'])
        base_tester.dump_yaml_specs(kwargs['specs_path'], overwrite)
        sys.stdout.write(f"Specification files generated in {kwargs['specs_path']}\n")

        if kwargs['validate']:
            try:
                features_spec = features.FeaturesSpec(kwargs['specs_path'])
            except features.FeaturesSpecError as error:
                sys.stderr.write(str(error) + '\n')
                return 1
            else:
                error = base_tester.validate_bases(features_spec)

                if error:
                    sys.stderr.write(
                        f'Expected class structure {features_spec.get_class_bases_text()} '
                        f'from docs does not match the defined one. {error}\n')
                    return 1

                sys.stdout.write('And validated\n')

        return 0


make_blueprint = MakeBlueprint()
patch_blueprint = PatchBlueprint()
check_pending_scenarios = CheckPendingScenarios()
make_yaml_specs = MakeYamlSpecs()
