from setuptools import setup, find_packages
from os.path import join, dirname

import jobs

setup(
    name='jobtechs',
    # the jobs/__init__.py should not contain references from install_requires
    version=jobs.__version__,
    packages=find_packages(),
    long_description=open(join(dirname(__file__), 'README.md')).read(),
    install_requires=['requests', 'lxml'],
    entry_points = {
        'console_scripts': [
            'extract_techs = jobs.scripts.extract_products:main2',
        ]
    }
)
