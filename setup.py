#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup

setup(
    name="ctypeslib2",
    version="2.2.1",
    description="ctypeslib2 - FFI toolkit, relies on clang",
    long_description=open("README.md").read(),
    author="Loic Jaquemet",
    author_email="loic.jaquemet+python@gmail.com",
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3.6",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    url="https://github.com/trolldbois/ctypeslib",
    download_url="https://github.com/trolldbois/ctypeslib/releases",
    license="License :: OSI Approved :: MIT License",
    packages=['ctypeslib',
              'ctypeslib.codegen',
              ],
    package_data={'ctypeslib': ['data/fundamental_type_name.tpl',
                                'data/pointer_type.tpl',
                                'data/headers.tpl']},
    entry_points={
        'console_scripts': [
            'clang2py = ctypeslib.clang2py:main',
        ]},
    test_suite="test.alltests",
    install_requires=[
        'clang>=3.7',
    ]
)
