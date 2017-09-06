# coding: utf8

from setuptools import setup, find_packages
setup(
    name="Cassini data analyzer",
    version="0.1",
    packages=find_packages(),
    scripts=['gen.py'],

    install_requires=[
     'python-igraph',
     'psycopg2',
     'pyshp',
     'scipy'
    ],

    package_data={'': ['*.qgs']},

    # metadata for upload to PyPI
    author="Bertrand Duménieu",
    author_email="bertrand.dumenieu@ehess.fr",
    description="This tool generates spatial graphs using the geohistoricaldata Cassini data.",
    license="WTFPL",
    keywords="cassini geohistoricaldata graph analysis",
    url="http://geohistoricaldata.org",   # project home page, if any
)



