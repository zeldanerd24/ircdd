#!/usr/bin/bash

cd `dirname $0`/dev-config
vagrant rsync
vagrant ssh -c "docker build -t ircdd-test ircdd/scripts/dev-config && docker run -v ircdd:/data/ircdd" 
