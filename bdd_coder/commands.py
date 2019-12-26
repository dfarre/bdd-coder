import os
import sys

from simple_cmd import decorators

from bdd_coder import LOGS_DIR_NAME
from bdd_coder import OK, FAIL

from bdd_coder.exceptions import (
    BaseTesterRetrievalError, FeaturesSpecError, InconsistentClassStructure,
    OverwriteError, Flake8Error)

from bdd_coder.coder import coders


@decorators.ErrorsCommand(FileNotFoundError, FeaturesSpecError, OverwriteError)
def make_blueprint(
    *, base_class=coders.DEFAULT_BASE_TEST_CASE,
    specs_path: 'Directory containing the YAML specs' = 'behaviour/specs',
    tests_path: 'Default: next to specs' = '', test_module_name='stories', overwrite=False
):
    coders.PackageCoder(
        base_class=base_class, specs_path=specs_path, tests_path=tests_path,
        test_module_name=test_module_name, overwrite=overwrite,
    ).create_tester_package()


@decorators.ErrorsCommand(BaseTesterRetrievalError, FeaturesSpecError, Flake8Error)
def patch_blueprint(
    test_module: 'Passed to `importlib.import_module`',
    specs_path: 'Directory to take new specs from. '
    f'Default: {coders.PackagePatcher.default_specs_dir_name}/ '
    'next to test package' = '', *, scenario_delimiter=coders.DEFAULT_SCENARIO_DELIMITER
):
    coders.PackagePatcher(test_module, specs_path, scenario_delimiter).patch()


@decorators.ErrorsCommand(
    BaseTesterRetrievalError, OverwriteError, FeaturesSpecError, InconsistentClassStructure)
def make_yaml_specs(
    test_module: 'Passed to `importlib.import_module`',
    specs_path: 'Will try to write the YAML files in here', *, overwrite=False,
):
    base_tester = coders.get_base_tester(test_module)
    features_spec = base_tester.features_spec(specs_path, overwrite)
    base_tester.validate_bases(features_spec)


class PendingScenariosError(Exception):
    pass


class LogsNotFoundError(Exception):
    pass


@decorators.ErrorsCommand(PendingScenariosError, LogsNotFoundError)
def check_pending_scenarios(logs_parent: f'Parent directory of {LOGS_DIR_NAME}/'):
    logs_dir = os.path.join(logs_parent, LOGS_DIR_NAME)

    if os.path.isdir(logs_dir):
        log_names = sorted(os.listdir(logs_dir))

        if log_names:
            with open(os.path.join(logs_dir, log_names[-1])) as log:
                lines = reversed(list(log))
                next(lines)
                message = next(lines).strip('\n')

            if message.endswith(OK) or message.endswith(FAIL):
                sys.stdout.write(message + '\n')
                return

            raise PendingScenariosError(
                f'Some scenarios did not run! Check the logs in {logs_dir}')

    raise LogsNotFoundError(f'No logs found in {logs_dir}')
