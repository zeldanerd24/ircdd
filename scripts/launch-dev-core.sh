#!/bin/bash

export SYNCED_FOLDER=`dirname $(pwd)`
export NUM_INSTANCES=1

cd `dirname $0`/config/dev-vagrant
vagrant up
vagrant ssh -c "/usr/bin/docker pull dockerfile/rethinkdb"
vagrant ssh -c "/usr/bin/docker pull dockerfile/nsq"
vagrant ssh -c "/usr/bin/docker pull dockerfile/python"
