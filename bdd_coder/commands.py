import argparse
import os
import subprocess

from bdd_coder import LOGS_DIR_NAME
from bdd_coder import SUCCESS_MSG
from bdd_coder.coder import coders


def bdd_blueprint():
    parser = argparse.ArgumentParser()
    parser.add_argument('--base-class', '-c', help='default: unittest.TestCase')
    parser.add_argument('--specs-path', '-i', help='default: behaviour/specs')
    parser.add_argument('--tests-path', '-o', help='default: next to specs')
    parser.add_argument('--pytest', action='store_true')
    kwargs = {k: v for k, v in parser.parse_args()._get_kwargs() if v is not None}
    test = kwargs.pop('pytest')

    coder = coders.PackageCoder(**kwargs)
    coder.create_tester_package()

    if test:
        subprocess.check_output(['pytest', '-vv', coder.tests_path])


def check_pending_scenarios(tests_path=''):
    parser = argparse.ArgumentParser()
    parser.add_argument('tests_path')
    logs_path = os.path.join(tests_path or parser.parse_args().tests_path, LOGS_DIR_NAME)

    if os.path.isdir(logs_path):
        log_names = sorted(os.listdir(logs_path))

        if log_names:
            with open(os.path.join(logs_path, log_names[-1]), 'rb') as log_bytes:
                log_bytes.seek(-5, 2)

                assert log_bytes.read().decode()[0] == '✅', (
                    f'✘ Some scenarios did not run! Check the logs in {logs_path}')

                return SUCCESS_MSG

    return 'No logs found'
