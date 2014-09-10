#!/bin/bash

PKG=ircdd

flake8 $PKG
nosetests $PKG
