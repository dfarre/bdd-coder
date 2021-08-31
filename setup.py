import configparser
import setuptools


ini = configparser.ConfigParser()
ini.read('version.ini')

with open('README.md', encoding='utf-8') as readme:
    long_description = readme.read()

tests_require = ['pytest-cov', 'freezegun', 'pytest-twisted', 'Twisted']

setuptools.setup(
    name=ini['version']['name'],
    version=ini['version']['value'],
    author='Daniel Farré Manzorro',
    author_email='d.farre.m@gmail.com',
    description='Gherkin language in class-based tests - test suite blueprinting',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://bitbucket.org/coleopter/bdd-coder',
    classifiers=[
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Environment :: Console',
        'Intended Audience :: Developers'],
    packages=setuptools.find_packages(),
    install_requires=['pyyaml', 'argparse', 'pygments', 'pytest', 'flake8', 'simple-cmd'],
    setup_requires=['setuptools', 'configparser'],
    tests_require=tests_require,
    extras_require={'dev': ['ipdb', 'ipython'], 'test': tests_require},
    entry_points={'console_scripts': [
        'bdd-blueprint=bdd_coder.commands:make_blueprint',
        'bdd-patch=bdd_coder.commands:patch_blueprint',
        'bdd-make-yaml-specs=bdd_coder.commands:make_yaml_specs']},
)
