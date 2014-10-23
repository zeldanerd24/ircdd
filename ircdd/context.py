from time import ctime
import yaml

from twisted import copyright
from twisted.cred import portal
from twisted.words import service

from ircdd import server
from ircdd.remote import RemoteReadWriter

userdata = dict(
    kzvezdarov='password',
    mcginnisdan='password',
    roman215='password',
    mikeharrison='password',
    kevinrothenberger='password'
    )


class ConfigStore(dict):
    """
    Container for configuration values and shared acces modules.
    """
    data = {'hostname': 'localhost',
            'port': '5799',
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
        stream = file(config.get('config'), 'r')
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

    # TODO: Make a custom realm that integrates with the database?
    ctx['realm'] = service.InMemoryWordsRealm(ctx['hostname'])
    ctx['realm'].addGroup(service.Group('placeholder_group'))

    # TODO: Make a custom checker & portal that integrate with the database?
    mock_db = server.InMemoryUsernamePasswordDatabaseDontUse(**userdata)
    ctx['portal'] = portal.Portal(ctx['realm'], [mock_db])

    ctx['server_info'] = dict(
        serviceName=ctx['realm'].name,
        serviceVersion=copyright.version,
        creationDate=ctime()
        )

    ctx['remote_rw'] = RemoteReadWriter(ctx['nsqd_tcp_addresses'],
                                        ctx['lookupd_http_addresses'],
                                        ctx['hostname'])

    return ctx
