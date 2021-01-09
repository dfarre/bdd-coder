import os
import sys

from simple_cmd.decorators import ErrorsCommand

from bdd_coder import OK, FAIL, COMPLETION_MSG

from bdd_coder.exceptions import (
    BaseTesterRetrievalError, FeaturesSpecError, InconsistentClassStructure,
    OverwriteError, Flake8Error, PendingScenariosError, LogsNotFoundError)

from bdd_coder.coder import coders


@ErrorsCommand(FileNotFoundError, FeaturesSpecError, OverwriteError)
def make_blueprint(*, base_class: 'Base test case class' = '',
                   specs_path: 'Directory containing the YAML specs' = 'behaviour/specs',
                   tests_path: 'Default: next to specs' = '',
                   test_module_name: 'Name for test_<name>.py' = 'stories',
                   overwrite=False):
    coders.PackageCoder(
        base_class=base_class, specs_path=specs_path, tests_path=tests_path,
        test_module_name=test_module_name, overwrite=overwrite,
    ).create_tester_package()


@ErrorsCommand(BaseTesterRetrievalError, FeaturesSpecError, Flake8Error)
def patch_blueprint(test_module: 'Passed to `importlib.import_module`',
                    specs_path: 'Directory to take new specs from. '
                    f'Default: {coders.PackagePatcher.default_specs_dir_name}/ '
                    'next to test package' = ''):
    coders.PackagePatcher(test_module, specs_path).patch()


@ErrorsCommand(BaseTesterRetrievalError, OverwriteError, FeaturesSpecError,
               InconsistentClassStructure)
def make_yaml_specs(test_module: 'Passed to `importlib.import_module`',
                    specs_path: 'Will try to write the YAML files in here',
                    *, overwrite=False):
    base_tester, _ = coders.get_base_tester(test_module)
    features_spec = base_tester.features_spec(specs_path, overwrite)
    base_tester.validate_bases(features_spec)


@ErrorsCommand(PendingScenariosError, LogsNotFoundError)
def check_pending_scenarios(logs_path: 'Path to BDD run logs file'):
    if os.path.isfile(logs_path):
        with open(logs_path, 'rb') as log:
            log.seek(-4, os.SEEK_END)  # 4 are the bytes of OK/FAIL (3) + \n (1)
            symbol = log.read().decode().strip()

        if symbol in (OK, FAIL):
            sys.stdout.write(f'{COMPLETION_MSG}. Check the logs in {logs_path}\n')
            return 0

        raise PendingScenariosError(logs_path=logs_path)

    raise LogsNotFoundError(logs_path=logs_path)
