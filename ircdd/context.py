from time import ctime
import yaml

from twisted import copyright
from twisted.cred import portal

from ircdd import server
from ircdd.server import ShardedRealm
from ircdd import cred
from ircdd.remote import RemoteReadWriter
from ircdd import database


class ConfigStore(dict):
    """
    Container for configuration values and shared acces modules.
    """
    data = {'hostname': 'localhost',
            'port': '5799',
            'rdb_port': '28015',
            'rdb_hostname': 'localhost',
            'nsqd_tcp_addresses': ['127.0.0.1:4150'],
            'lookupd_http_addresses': ['127.0.0.1:4161'],
            }

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

    # TODO: Initialize DB driver
    # ctx['rethinkdb'] =

    ctx['realm'] = ShardedRealm(ctx, ctx['hostname'])

    cred_checker = cred.DatabaseCredentialsChecker(ctx)
    ctx['portal'] = portal.Portal(ctx['realm'], [cred_checker])

    db = database.IRCDDatabase(ctx['rdb_hostname'],  ctx['rdb_port'])
    db.initializeDB()
    db.addUser('kzvezdarov', 'kzvezdarov@gmail.com', 'password', True, '')
    db.addUser('mcginnisdan', 'mcginnis.dan@gmail.com', 'password', True, '')
    db.addUser('roman215', 'Roman215@comcast.net', 'password', True, '')
    db.addUser('mikeharrison', 'tud04305@temple.edu', 'password', True, '')
    db.addUser('kevinrothenberger', 'tud14472@temple.edu',
               'password', True, '')
    db.addChannel('#ircdd', 'kzvezdarov', 'private')
    ctx['server_info'] = dict(
        serviceName=ctx['realm'].name,
        serviceVersion=copyright.version,
        creationDate=ctime()
        )

    ctx['remote_rw'] = RemoteReadWriter(ctx['nsqd_tcp_address'],
                                        ctx['lookupd_http_address'],
                                        ctx['hostname'])

    return ctx
