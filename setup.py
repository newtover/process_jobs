from setuptools import setup, find_packages
import setuptools.command.test
from os.path import join, dirname

import jobtechs


class TestCommand(setuptools.command.test.test):
    """Setuptools test command explicitly using test discovery."""
    def _test_args(self):
        yield 'discover'
        yield from super()._test_args()


setup(
    name='jobtechs',
    # the jobs/__init__.py should not contain references from install_requires
    version=jobtechs.__version__,
    packages=find_packages(),
    long_description=open(join(dirname(__file__), 'README.md')).read(),
    install_requires=['requests', 'lxml'],
    entry_points = {
        'console_scripts': [
            'extract_techs = jobtechs.scripts.extract_techs:main2',
        ]
    },
    test_suite = 'tests',
    cmdclass = {
        'test': TestCommand,
    },
)
