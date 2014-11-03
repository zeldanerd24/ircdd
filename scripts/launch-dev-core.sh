#!/bin/bash

cd `dirname $0`/dev-config
vagrant up
vagrant ssh -c "/usr/bin/docker build -t ircdd-dev /home/core/ircdd/scripts/dev-config"
vagrant ssh -c "/usr/bin/docker pull dockerfile/rethinkdb"
vagrant ssh -c "/usr/bin/docker pull dockerfile/nsq"