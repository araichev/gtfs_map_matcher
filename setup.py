from setuptools import setup, find_packages


# Import ``__version__`` variable
exec(open('gtfs_map_matcher/_version.py').read())

with open('README.rst') as f:
    readme = f.read()

with open('LICENSE.txt') as f:
    license = f.read()

setup(
    name='gtfs_map_matcher',
    version=__version__,
    author='Alexander Raichev',
    url='https://github.com/araichev/gtfs_map_matcher',
    description='A Python 3.4+ library to match GTFS feeds to Open Street Map',
    long_description=readme,
    license=license,
    install_requires=[
        'gtfstk>=9.0.2',
        'requests-futures>=0.9.7',
    ],
    packages=find_packages(exclude=('tests', 'docs'))
)
