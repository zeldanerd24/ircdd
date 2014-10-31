#! /bin/bash

cd `dirname $0`/dev-config
vagrant rsync
vagrant ssh -c "fleetctl stop ircdd.service"
vagrant ssh -c "fleetctl destroy ircdd.service"
vagrant ssh -c "fleetctl start ircdd/scripts/dev-config/services/ircdd.service"
vagrant ssh -c "fleetctl stop rethinkdb@.service"
vagrant ssh -c "fleetctl destroy rethinkdb@.service"
vagrant ssh -c "fleetctl stop rethinkdb@ircdd.service"
vagrant ssh -c "fleetctl destroy rethinkdb@ircdd.service"
vagrant ssh -c "fleetctl submit ircdd/scripts/dev-config/services/rethinkdb@.service"
vagrant ssh -c "fleetctl start ircdd/scripts/dev-config/service/rethinkdb@ircdd.service"
