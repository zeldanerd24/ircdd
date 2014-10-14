from zope.interface import implements
from twisted.words.service import IRCUser
from twisted.application import internet
from twisted.internet import protocol
from twisted.internet import defer
from twisted.python import failure
from twisted.cred import checkers, error, credentials
from twisted.words import service
from twisted.words.protocols import irc


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

        #replace twisted server functions with ones we're using instead
        setattr(service.IRCUser, "irc_NICK", irc_NICK)
        setattr(service.IRCUser, "irc_JOIN", irc_JOIN)

        self.ctx = ctx


def makeServer(ctx):
    """
    Creates and initializes an IRCDDFactory with the given context.
    Returns:
        A TCP server running on the specified port, serving
        requests via the IRCDDFactory
    """
    f = IRCDDFactory(ctx)

    irc_server = internet.TCPServer(int(ctx['port']), f)
    return irc_server


#In memory storage and checking of nicknames/passwords
#If user name is not found, it adds the user to the list
class InMemoryUsernamePasswordDatabaseDontUse:
    """
    An extremely simple credentials checker.

    This is only of use in one-off test programs or examples which don't
    want to focus too much on how credentials are verified.

    You really don't want to use this for anything else.  It is, at best, a
    toy.  If you need a simple credentials checker for a real application,
    see L{FilePasswordDB}.
    """

    implements(checkers.ICredentialsChecker)

    credentialInterfaces = (credentials.IUsernamePassword,
                            credentials.IUsernameHashedPassword)

    def __init__(self, **users):
        self.users = users

    def addUser(self, username, password):
        self.users[username] = password

    def _cbPasswordMatch(self, matched, username):
        if matched:
            return username
        else:
            return failure.Failure(error.UnauthorizedLogin())

    def requestAvatarId(self, credentials):
        if credentials.username in self.users:
            return defer.maybeDeferred(
                credentials.checkPassword,
                self.users[credentials.username]).addCallback(
                self._cbPasswordMatch, str(credentials.username))
        else:
            #this may need to be changed if we use encrypted credentials
            self.users[credentials.username] = credentials.password
            return self.requestAvatarId(credentials)


#Updated join channel method to allow creating channels that don't exist
#Replaces a twisted function with same name in service.IRCUser
def irc_JOIN(self, prefix, params):
    """Join message

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
        #if channel is not found, then add it and call this function again
        self.realm.addGroup(service.Group(groupName))
        self.irc_JOIN(prefix, params)
        return
    self.realm.getGroup(groupName).addCallbacks(cbGroup, ebGroup)


#Updated nickname checking function which allows for anonymous connection
#Replaces a twisted function with same name in service.IRCUser
def irc_NICK(self, prefix, params):
    """Nick message -- Set your nickname.

    Parameters: <nickname>

    [REQUIRED]
    """
    nickname = params[0]
    try:
        nickname = nickname.decode(self.encoding)
    except UnicodeDecodeError:
        self.privmsg(
            NICKSERV,
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
