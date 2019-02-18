import setuptools


tests_require = ['pytest']

setuptools.setup(
    name='bdd-coder',
    packages=setuptools.find_packages(),
    install_requires=['pyyaml', 'argparse'],
    setup_requires=['setuptools'],
    tests_require=tests_require,
    extras_require={'dev': ['ipdb', 'ipython'], 'test': tests_require},
    entry_points={'console_scripts': ['bdd-blueprint=bdd_coder.cmd:bdd_blueprint']},
)
