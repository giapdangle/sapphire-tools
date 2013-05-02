
from setuptools import setup

setup(
    name='sapphire',
    
    version='0.9dev',
    
    packages=['sapphire',
              'sapphire.core',
              'sapphire.buildtools',
              'sapphire.apiserver',
              'sapphire.deviceserver',
              'sapphire.automaton',
              'sapphire.devices',
              'sapphire.tftp'],

    package_data={'sapphire.buildtools': ['settings.json', 'linker.x', 'project_template/*']},

    scripts=['scripts/sapphireconsole.py',
             'scripts/sapphiremake.py',
             'scripts/sapphire_apiserver.py',
             'scripts/sapphire_deviceserver.py',
             'scripts/sapphire_automaton.py'],

    license='License :: OSI Approved :: Mozilla Public License 2.0 (MPL 2.0)',

    description='Sapphire Tools',

    long_description=open('README.txt').read(),

    install_requires=[
        "gevent >= 0.13.8",
        "greenlet >= 0.4.0",
        "bottle >= 0.11.4",
        "beaker >= 1.6.4",
        "pyserial >= 2.6",
        "bitstring >= 3.0.2",
        "cmd2 >= 0.6.3",
        "crcmod >= 1.7",
        "pyparsing >= 1.5.6, < 2.0",
        "APScheduler >= 2.1.0",
        "intelhex >= 1.3",
        "appdirs >= 1.2.0",
        "supervisor >= 3.0b1",
        "redis >= 2.7.2",
        "pydispatcher >= 2.0.3",
    ]
)





