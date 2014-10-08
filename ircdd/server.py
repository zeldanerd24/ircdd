from twisted.words.service import IRCUser
from twisted.application import internet
from twisted.internet import protocol


class IRCDDFactory(protocol.ServerFactory):
    """
    Server factory which creates instances of the modified
    IRC protocol.
    """
    protocol = IRCUser

    def __init__(self, ctx):
        # This is to support the stock IRCUser.
        # For other components, use ctx instead
        self.realm = ctx['realm']
        self.portal = ctx['portal']
        self._serverInfo = ctx['server_info']

        self.ctx = ctx


def makeServer(ctx):
    """
    Creates and initializes an IRCDDFactory with the given context.
    Returns:
        A TCP server running on the specified port, serving
        requests via the IRCDDFactory
    """
    f = IRCDDFactory(ctx)

    irc_server = internet.TCPServer(ctx['port'], f)
    return irc_server
