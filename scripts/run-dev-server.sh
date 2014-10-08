#! /bin/bash

cd `dirname $0`/dev-config
vagrant rsync
vagrant ssh -c "fleetctl stop ircdd.service"
vagrant ssh -c "fleetctl destroy ircdd.service"
vagrant ssh -c "fleetctl start ircdd/scripts/dev-config/services/ircdd.service"
