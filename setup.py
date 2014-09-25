#! /usr/bin/env python2.7
import ez_setup
ez_setup.use_setuptools()

from setuptools import setup, find_packages

setup(name="ircdd",
      version="alpha",
      description="Distributed IRC Daemon",
      url="github.com/kzvezdarov/ircdd",
      license="GPL v3.0 or later",
      install_requires=['twisted', ],
      setup_requires=["flake8", "nose", ],
      packages=find_packages(),
      scripts=["bin/ircdd.py", ],
      test_suite="nosetests",
      )
