from simple_cmd.decorators import ErrorsCommand

from bdd_coder.exceptions import (
    BaseTesterRetrievalError, FeaturesSpecError, InconsistentClassStructure,
    OverwriteError, Flake8Error, ScenarioMismatchError)

from bdd_coder import coders


@ErrorsCommand(FileNotFoundError, FeaturesSpecError, OverwriteError)
def make_blueprint(*,
                   specs_path: 'Directory containing the YAML specs' = 'behaviour/specs',
                   tests_path: 'Default: next to specs' = '',
                   test_module_name: 'Name for test_<name>.py' = 'stories',
                   overwrite=False,
                   run_pytest=False):
    coders.PackageCoder(
        specs_path=specs_path, tests_path=tests_path,
        test_module_name=test_module_name, overwrite=overwrite,
    ).create_tester_package(run_pytest=run_pytest)


@ErrorsCommand(BaseTesterRetrievalError, FeaturesSpecError, Flake8Error, ScenarioMismatchError)
def patch_blueprint(test_module: 'Passed to `importlib.import_module`',
                    specs_path: 'Directory to take new specs from. '
                    f'Default: {coders.PackagePatcher.default_specs_dir_name}/ '
                    'next to test package' = '', *, run_pytest=False):
    coders.PackagePatcher(test_module, specs_path).patch(run_pytest=run_pytest)


@ErrorsCommand(BaseTesterRetrievalError, OverwriteError, FeaturesSpecError,
               InconsistentClassStructure)
def make_yaml_specs(test_module: 'Passed to `importlib.import_module`',
                    specs_path: 'Will try to write the YAML files in here',
                    *, overwrite=False):
    base_tester, _ = coders.get_base_tester(test_module)
    features_spec = base_tester.features_spec(specs_path, overwrite)
    base_tester.validate_bases(features_spec)
