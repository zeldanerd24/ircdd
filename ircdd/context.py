from time import ctime
import yaml

from twisted import copyright
from twisted.cred import portal

from ircdd.server import ShardedRealm
from ircdd import cred
from ircdd.remote import RemoteReadWriter
from ircdd import database


class ConfigStore(dict):
    """
    Container for configuration values and shared acces modules.
    """
    data = {}

    def __getitem__(self, key):
        return self.data[key]

    def __setitem__(self, key, item):
        self.data[key] = item


def makeContext(config):
    """
    Constructs an initialized context from the config values.
    Returns:
        A dict mapping keys to available resources,
        including the original config values.
    """

    ctx = ConfigStore()

    # if user specified a configuration file
    # overwrite defaults with values from file
    if config.get('config') is not None:
        stream = open(config.get('config'), 'r')
        del config['config']
        # yaml.load turns a file into an object/dictionary
        conFile = yaml.load(stream)
        stream.close()
        for x in conFile:
            ctx[x] = conFile.get(x)

    # if user specified any values via command line
    # overwrite existing values
    for x in config:
        ctx[x] = config.get(x)

    ctx['realm'] = ShardedRealm(ctx, ctx['hostname'])

    cred_checker = cred.DatabaseCredentialsChecker(ctx)
    ctx['portal'] = portal.Portal(ctx['realm'], [cred_checker])

    ctx["db"] = database.IRCDDatabase(db=ctx["db"],
                                      host=ctx['rdb_hostname'],
                                      port=ctx['rdb_port'])

    ctx['server_info'] = dict(
        serviceName=ctx['realm'].name,
        serviceVersion=copyright.version,
        creationDate=ctime()
        )

    ctx['remote_rw'] = RemoteReadWriter(ctx['nsqd_tcp_address'],
                                        ctx['lookupd_http_address'],
                                        ctx['hostname'])

    return ctx
