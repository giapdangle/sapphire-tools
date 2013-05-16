
from setuptools import setup

setup(
    name='sapphire',
    
    version='0.9dev',
    
    license='License :: OSI Approved :: Mozilla Public License 2.0 (MPL 2.0)',

    description='Sapphire Tools',

    long_description=open('README.txt').read(),

    install_requires=[
        "sapphire-kv >= 0.9_dev_2",
        "sapphire-devices >= 0.9_dev_2",
    ]
)



