import setuptools


tests_require = ['pytest-cov', 'flake8', 'freezegun']

setuptools.setup(
    name='bdd-coder',
    version='1.0',
    packages=setuptools.find_packages(),
    install_requires=['pyyaml', 'argparse', 'pytest'],
    setup_requires=['setuptools'],
    tests_require=tests_require,
    extras_require={'dev': ['ipdb', 'ipython'], 'test': tests_require},
    entry_points={'console_scripts': [
        'bdd-blueprint=bdd_coder.commands:make_blueprint',
        'bdd-patch=bdd_coder.commands:patch_blueprint',
        'bdd-pending-scenarios=bdd_coder.commands:check_pending_scenarios',
        'bdd-make-yaml-specs=bdd_coder.commands:make_yaml_specs']},
)
