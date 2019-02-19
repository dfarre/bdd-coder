import argparse
import subprocess

from bdd_coder import coders


def bdd_blueprint():
    parser = argparse.ArgumentParser()
    parser.add_argument('--base-class', '-c', help='default: unittest.TestCase')
    parser.add_argument('--specs-path', '-i', help='default: behaviour/specs')
    parser.add_argument('--tests-path', '-o', help='default: next to specs')
    parser.add_argument('--pytest', action='store_true')
    kwargs = {k: v for k, v in parser.parse_args()._get_kwargs() if v is not None}
    test = kwargs.pop('pytest')

    coder = coders.Coder(**kwargs)
    coder.create_package()

    if test:
        subprocess.check_output(['pytest', coder.tests_path])
