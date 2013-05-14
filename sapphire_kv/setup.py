
from setuptools import setup

setup(
    name='sapphire-kv',
    
    version='0.9_dev_2',
    
    packages=['sapphire',
              'sapphire.core',
              'sapphire.apiserver',
              'sapphire.automaton'],

    scripts=['scripts/sapphire_apiserver.py',
             'scripts/sapphire_automaton.py'],

    license='License :: OSI Approved :: Mozilla Public License 2.0 (MPL 2.0)',

    description='Sapphire Key Value System',

    long_description=open('README.txt').read(),

    install_requires=[
        "bottle >= 0.11.4",
        "beaker >= 1.6.4",
        "APScheduler >= 2.1.0",
        "appdirs >= 1.2.0",
        "supervisor >= 3.0b1",
        "redis >= 2.7.2",
        "pydispatcher >= 2.0.3",
    ]
)





