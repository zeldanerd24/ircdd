from twisted.application import internet
from twisted.internet import protocol

from ircdd.protocol import IRCDDUser


class IRCDDFactory(protocol.ServerFactory):
    """
    Factory which creates instances of the :class:`ircdd.server.IRCDDUser`
    protocol. Expects to receive an initialized context object at creation.

    :param ctx: A :class:`ircdd.context.ConfigStore` object which contains both
    the raw config values and the initialized shared drivers.
    """

    def __init__(self, ctx):
        # This is to support the stock IRCUser.
        # For other components, use ctx instead
        self.ctx = ctx
        self.realm = ctx['realm']
        self.portal = ctx['portal']
        self._serverInfo = ctx['server_info']

    protocol = IRCDDUser


def makeServer(ctx):
    """
    Creates and initializes an :class:`ircdd.server.IRCDDFactory`
    with the given context.
    Returns a :class:`twisted.internet.TCPServer` running on the
    specified `port`.

    :param ctx: a :class:`ircdd.context.ConfigStore` object that
    contains both the raw config values and the initialized shared
    drivers.

    """
    f = IRCDDFactory(ctx)
    IRCDDUser.ctx = ctx

    irc_server = internet.TCPServer(int(ctx['port']), f)
    return irc_server
