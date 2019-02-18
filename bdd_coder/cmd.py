import argparse
import subprocess

from bdd_coder import coders


def bdd_blueprint():
    parser = argparse.ArgumentParser()
    parser.add_argument('--base-class', '-c', default='unittest.TestCase')
    parser.add_argument('--specs-path', '-i', default='behaviour/specs')
    parser.add_argument('--tests-path', '-o', default='behaviour/tests')
    parser.add_argument('--pytest', action='store_true')
    args = parser.parse_args()

    coder = coders.Coder(args.base_class, args.specs_path, args.tests_path)
    coder.create_package()

    if args.pytest:
        subprocess.check_output(['pytest', args.tests_path])
