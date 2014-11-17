#! /bin/bash

export SYNCED_FOLDER=`dirname $(pwd)`

cd `dirname $0`/config/dev-vagrant

vagrant rsync

vagrant ssh -c "ircdd/scripts/config/dev-vagrant/reload-all.sh"
