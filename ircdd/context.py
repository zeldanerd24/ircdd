from time import ctime

from twisted import copyright
from twisted.cred import portal, checkers
from twisted.words import service

userdata = dict(
    kzvezdarov='password',
    mcginnisdan='password',
    roman215='password',
    mikeharrison='password',
    kevinrothenberger='password'
    )


def makeContext(config):
    """
    Constructs an initialized context from the config values.
    Returns:
        A dict mapping keys to available resources,
        including the original config values.
    """
    ctx = dict(config)

    # TODO: Initialize DB driver
    # ctx.rethinkdb =
    # TODO: Initialize NSQ driver
    # ctx.nsq =

    # TODO: Make a custom realm that integrates with the database?
    ctx['realm'] = service.InMemoryWordsRealm('placeholder_realm')
    ctx['realm'].addGroup(service.Group('placeholder_group'))

    # TODO: Make a custom checker & portal that integrate with the database?
    mock_db = checkers.InMemoryUsernamePasswordDatabaseDontUse(**userdata)
    ctx['portal'] = portal.Portal(ctx['realm'], [mock_db])

    ctx['server_info'] = dict(
        serviceName=ctx['realm'].name,
        serviceVersion=copyright.version,
        creationDate=ctime()
        )
    return ctx
