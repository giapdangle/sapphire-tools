
from setuptools import setup

setup(
    name='sapphire-devices',
    
    version='0.9_dev_2',

    packages=['sapphiredevices',
              'sapphiredevices.buildtools',
              'sapphiredevices.deviceserver',
              'sapphiredevices.devices',
              'sapphiredevices.tftp'],

    package_data={'sapphire.buildtools': ['settings.json', 'linker.x', 'project_template/*']},

    scripts=['scripts/sapphireconsole.py',
             'scripts/sapphire_deviceserver.py',
             'scripts/sapphire_devicesetup.py'],

    license='License :: OSI Approved :: Mozilla Public License 2.0 (MPL 2.0)',

    description='Sapphire Device Tools',

    long_description=open('README.txt').read(),

    install_requires=[
        "sapphire >= 0.9_dev_2",
        "pyserial >= 2.6",
        "bitstring >= 3.0.2",
        "cmd2 >= 0.6.3",
        "crcmod >= 1.7",
        "pyparsing >= 1.5.6, < 2.0",
        "intelhex >= 1.3",
        "pydispatcher >= 2.0.3",
    ]
)





