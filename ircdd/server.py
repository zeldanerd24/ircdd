from twisted.words.service import IRCUser
from twisted.application import internet
from twisted.internet import protocol
from twisted.words import service
from twisted.words.protocols import irc
from ircdd import database


class IRCDDUser(IRCUser):
    """
    Contains replacement methods for the twisted protocol default methods.
    """

    ctx = None

    # Updated join channel method to allow creating channels that don't exist
    # Replaces a twisted function with same name in service.IRCUser
    def irc_JOIN(self, prefix, params):
        """
        Replacement Twisted IRC Join channel method
        Creates a nonexisting channel on join attmept
        Parameters: ( <channel> *( "," <channel> ) [ <key> *( "," <key> ) ] )
        """
        try:
            groupName = params[0].decode(self.encoding)
        except UnicodeDecodeError:
            self.sendMessage(
                irc.ERR_NOSUCHCHANNEL, params[0],
                ":No such channel (could not decode your unicode!)")
            return
        if groupName.startswith('#'):
            groupName = groupName[1:]

        def cbGroup(group):
            def cbJoin(ign):
                self.userJoined(group, self)
                self.names(
                    self.name,
                    '#' + group.name,
                    [user.name for user in group.iterusers()])
                self._sendTopic(group)
            return self.avatar.join(group).addCallback(cbJoin)

        def ebGroup(err):
            db = database.IRCDDatabase(self.ctx['rdb_hostname'],
                                       self.ctx['rdb_port'])
            # if channel is not found, then add it and call this function again
            if db.getChannel(groupName) is None:
                db.addChannel(groupName, '', 'public')
            self.realm.addGroup(service.Group(groupName))
            self.irc_JOIN(prefix, params)
            return
        self.realm.getGroup(groupName).addCallbacks(cbGroup, ebGroup)

    # Updated nickname checking function which allows for anonymous connection
    # Replaces a twisted function with same name in service.IRCUser
    def irc_NICK(self, prefix, params):
        """Nick message -- Set your nickname.

        Replacement of the Twisted method
        Instead of NickServ messaging you on empty password,
        it ignores and allows an empty password.

        Parameters: <nickname>

        [REQUIRED]
        """
        nickname = params[0]
        try:
            nickname = nickname.decode(self.encoding)
        except UnicodeDecodeError:
            self.privmsg(
                service.NICKSERV,
                nickname,
                'Your nickname cannot be decoded. Please use ASCII or UTF-8.')
            self.transport.loseConnection()
            return

        self.nickname = nickname
        self.name = nickname

        for code, text in self._motdMessages:
            self.sendMessage(code, text % self.factory._serverInfo)

        if self.password is None:
            self.password = ''
        password = self.password
        self.password = None
        self.logInAs(nickname, password)


class IRCDDFactory(protocol.ServerFactory):
    """
    Server factory which creates instances of the modified
    IRC protocol.
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
    Creates and initializes an IRCDDFactory with the given context.
    Returns:
        A TCP server running on the specified port, serving
        requests via the IRCDDFactory
    """
    f = IRCDDFactory(ctx)
    IRCDDUser.ctx = ctx

    irc_server = internet.TCPServer(int(ctx['port']), f)
    return irc_server
