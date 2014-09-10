#! /usr/bin/env python2.7
from distutils.core import setup

setup(name="ircdd",
      version="pre-dev",
      description="Distributed IRC Daemon",
      long_descriptin=open("README.txt").read(),
      url="github.com/kzvezdarov/ircdd",
      license="GPL v3.0 or later",
      packages=["ircdd",],
      scripts=["bin/ircdd.py",],
      )
