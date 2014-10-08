#!/bin/bash

cd `dirname $0`/dev-config
vagrant rsync
vagrant ssh -c "docker build -t ircdd-test ircdd/scripts/dev-config && docker run -v /home/core/ircdd:/data ircdd-test bash -c  \"python setup.py flake8 && python setup.py nosetests && python setup.py install\""
