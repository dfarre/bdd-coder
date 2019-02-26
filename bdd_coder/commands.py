import argparse
import os
import subprocess
import sys

from bdd_coder import LOGS_DIR_NAME
from bdd_coder import SUCCESS_MSG
from bdd_coder.coder import coders


def bdd_blueprint():
    parser = argparse.ArgumentParser()
    parser.add_argument('--base-class', '-c', help='default: unittest.TestCase')
    parser.add_argument('--specs-path', '-i', help='default: behaviour/specs')
    parser.add_argument('--tests-path', '-o', help='default: next to specs')
    parser.add_argument('--tests-module-name', '-n', help='default: stories (test_stories.py)')
    parser.add_argument('--pytest', action='store_true', help='run pytest on the blueprint')
    kwargs = {k: v for k, v in parser.parse_args()._get_kwargs() if v is not None}
    test = kwargs.pop('pytest')

    coder = coders.PackageCoder(**kwargs)
    coder.create_tester_package()

    if test:
        subprocess.check_output(['pytest', '-vv', coder.tests_path])


def check_pending_scenarios(logs_parent=''):
    parser = argparse.ArgumentParser()
    parser.add_argument('logs_parent')
    logs_dir = os.path.join(logs_parent or parser.parse_args().logs_parent, LOGS_DIR_NAME)

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
