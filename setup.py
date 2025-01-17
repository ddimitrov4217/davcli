# -*- coding: UTF-8 -*-
# vim:ft=python:et:ts=4:sw=4:ai

from setuptools import setup, find_packages


setup(
    name='davcli',
    version='1.1',
    description='WebDav Sync for swtrac',
    long_description='WebDav Sync for swtrac command line interface',
    author='Dimitar Lyubomirov Dimitrov',
    author_email='ddimitrov4217@gmail.com',
    url='https://github.com/ddimitrov4217/davcli/',
    install_requires=['click', 'pytz'],
    setup_requires=[],
    packages=find_packages(exclude=['ez_setup']),
    include_package_data=True,
    package_data={'davcli': ['i18n/*/LC_MESSAGES/*.mo']},
    scripts=['contrib/swtrac_download.sh'],
    zip_safe=False,
    license='GPL',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Programming Language :: Python :: 3',
        'Operating System :: OS Independent',
        'Environment :: Console',
        'License :: OSI Approved :: GNU General Public License (GPL)',
        'Natural Language :: Bulgarian',
        'Intended Audience :: Developers',
        'Topic :: Utilities',
        'Topic :: System :: Archiving :: Mirroring',
        'Topic :: Communications :: File Sharing',
    ],
    entry_points={
        'console_scripts': [
            'davcli=davcli.__main__:cli_tools',
        ],
    },
)
