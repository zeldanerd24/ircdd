#!/bin/bash

cd `dirname $0`/dev-config
vagrant rsync
vagrant ssh -c "fleetctl destroy ircdd && fleetctl start --block-attempts=100 ircdd/scripts/dev-config/services/ircdd.service"

if vagrant ssh -c "fleetctl status ircdd" | grep "failed"; then
    vagrant ssh -c "fleetctl status ircdd"
else
    echo "All clear"
fi
