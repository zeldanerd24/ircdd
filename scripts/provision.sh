#!/bin/bash

set -ev

# Tools
sudo apt-get install -y python-pip
sudo pip install flake8

# Dependencies
sudo pip install nose
sudo pip install twisted

# Install release
sudo python setup.py install
