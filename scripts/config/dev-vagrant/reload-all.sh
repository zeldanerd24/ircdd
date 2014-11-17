#!/bin/bash

fleetctl destroy rethinkdb@1
fleetctl destroy rethinkdb-discovery@1
fleetctl destroy rethinkdb@.service
fleetctl destroy rethinkdb-discovery@.service

fleetctl submit ircdd/scripts/services/rethinkdb@.service
fleetctl submit ircdd/scripts/services/rethinkdb-discovery@.service

fleetctl start rethinkdb@1
fleetctl start rethinkdb-discovery@1

fleetctl destroy nsqlookupd@1
fleetctl destroy nsqlookupd-discovery@1
fleetctl destroy nsqd
fleetctl destroy nsqlookupd@.service
fleetctl destroy nsqlookupd-discovery@.service
fleetctl destroy nsqd.service

fleetctl submit ircdd/scripts/services/nsqlookupd@.service
fleetctl submit ircdd/scripts/services/nsqlookupd-discovery@.service
fleetctl submit ircdd/scripts/services/nsqd.service

fleetctl start nsqlookupd@1
fleetctl start nsqlookupd-discovery@1
fleetctl start nsqd

fleetctl destroy dev-ircdd@1
fleetctl destroy dev-ircdd@.service

fleetctl submit ircdd/scripts/services/dev-ircdd@.service
fleetctl start dev-ircdd@1
