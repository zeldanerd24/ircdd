#! /bin/bash

cd `dirname $0`/dev-config
vagrant rsync
# Enable database
vagrant ssh -c "fleetctl stop rethinkdb@.service"
vagrant ssh -c "fleetctl destroy rethinkdb@.service"
vagrant ssh -c "fleetctl stop rethinkdb@ircdd.service"
vagrant ssh -c "fleetctl destroy rethinkdb@ircdd.service"
vagrant ssh -c "fleetctl submit ircdd/scripts/dev-config/services/rethinkdb@.service"
vagrant ssh -c "fleetctl start ircdd/scripts/dev-config/services/rethinkdb@ircdd.service"
rethinkdb import -d ./rethinkdb_base_export
# Enable message queue search
vagrant ssh -c "fleetctl stop nsqlookupd@.service"
vagrant ssh -c "fleetctl destroy nsqlookupd@.service"
vagrant ssh -c "fleetctl stop nsqlookupd@search.service"
vagrant ssh -c "fleetctl destroy nsqlookupd@search.service"
vagrant ssh -c "fleetctl submit ircdd/scripts/dev-config/services/nsqlookupd@.service"
vagrant ssh -c "fleetctl start ircdd/scripts/dev-config/services/nsqlookupd@search.service"
# Enable message queue admin
vagrant ssh -c "fleetctl stop nsqadmin@.service"
vagrant ssh -c "fleetctl destroy nsqadmin@.service"
vagrant ssh -c "fleetctl stop nsqadmin@first.service"
vagrant ssh -c "fleetctl destroy nsqadmin@first.service"
vagrant ssh -c "fleetctl submit ircdd/scripts/dev-config/services/nsqadmin@.service"
vagrant ssh -c "fleetctl start ircdd/scripts/dev-config/services/nsqadmin@first.service"
# Enable message queue
vagrant ssh -c "fleetctl stop nsqd.service"
vagrant ssh -c "fleetctl destroy nsqd.service"
vagrant ssh -c "fleetctl start ircdd/scripts/dev-config/services/nsqd.service"
# Enable server
vagrant ssh -c "fleetctl stop ircdd@.service"
vagrant ssh -c "fleetctl destroy ircdd@.service"
vagrant ssh -c "fleetctl stop ircdd@server.service"
vagrant ssh -c "fleetctl destroy ircdd@server.service"
vagrant ssh -c "fleetctl submit ircdd/scripts/dev-config/services/ircdd@.service"
vagrant ssh -c "fleetctl start ircdd/scripts/dev-config/services/ircdd@server.service"
