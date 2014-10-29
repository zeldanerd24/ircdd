from zope.interface import implements
from twisted.words.service import IRCUser, Group, User, WordsRealm
from twisted.application import internet
from twisted.internet import protocol, defer
from twisted.python import failure, log
from twisted.cred import checkers, error, credentials
from twisted.words import service, ewords
from twisted.words.protocols import irc


class ShardedUser(User):
    def __init__(self, ctx, name):
        super(ShardedUser, self).__init__(name)
        self.ctx = ctx

    def send(self, recipient, message):
        log.msg("MESSAGE %s to %s" % (str(message), str(recipient)))
        super(ShardedUser, self).send(recipient, message)


class ShardedGroup(Group):
    def __init__(self, ctx, name):
        super(ShardedGroup, self).__init__(name)
        self.ctx = ctx

    def receiveRemote(self, message):
        # discard if originated here
        pass


class IRCDDRealm(WordsRealm):
    def __init__(self, ctx, *a, **kw):
        super(IRCDDRealm, self).__init__(*a, **kw)
        self.ctx = ctx
        self.users = {}
        self.groups = {}

    def userFactory(self, name):
        return ShardedUser(self.ctx, name)

    def groupFactory(self, name):
        return ShardedGroup(self.ctx, name)

    def itergroups(self):
        # Add a lookup for remote groups?
        return defer.succeed(self.groups.itervalues())

    def addUser(self, user):
        # check straight in the DB's user list
        if user.name in self.users:
            return defer.fail(failure.Failure(ewords.DuplicateUser()))

        self.users[user.name] = user
        return defer.succeed(user)

    def addGroup(self, group):
        if group.name in self.groups:
            return defer.fail(failure.Failure(ewords.DuplicateGroup()))

        self.groups[group.name] = group
        return defer.succeed(group)

    def lookupUser(self, name):
        assert isinstance(name, unicode)
        name = name.lower()
        # Lookup in database also? Not sure what this
        # method does
        try:
            user = self.users[name]
        except KeyError:
            return defer.fail(failure.Failure(ewords.NoSuchUser(name)))
        else:
            return defer.succeed(user)

    def lookupGroup(self, name):
        assert isinstance(name, unicode)
        name = name.lower()

        try:
            group = self.groups[name]
        except KeyError:
            return defer.fail(failure.Failure(ewords.NoSuchGroup(name)))
        else:
            return defer.succeed(group)


class IRCDDUser(IRCUser):
    """
    A simple integration layer on top of :class:`twisted.words.service.IRCUser`
    which integrates it with `NSQ` and `RethinkDB` to allow for server linking
    and state persistance.
    """

    def irc_JOIN(self, prefix, params):
        """
        Handles `/join #<channel>`. First, looks up the group
        in the realm. If the group does not exist, references the
        database. If the group does not exist there as well (which implies
        that it does not exist on any server in the cluster), it is created
        locally and committed to the database. Finally, after the join is
        authorized, publishes the join message both to the local group and
        on the NSQ topic.
        """
        log.msg("AVATAR %s" % str(self.avatar))
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
            # if channel is not found, then add it and call this function again
            self.realm.addGroup(service.Group(groupName))
            self.irc_JOIN(prefix, params)
            return
        self.realm.getGroup(groupName).addCallbacks(cbGroup, ebGroup)

    def irc_NICK(self, prefix, params):
        """
        Handles `/nick <nickname>`. If the nickname exists, is not in use,
        and is password protected (or the `strict` flag has been set), decline
        and request password. If the nickname is not in use and `strict` is
        off, create it log the user in with it.
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
    Factory which creates instances of the :class:`ircdd.server.IRCDDUser`
    protocol. Expects to receive an initialized context object at creation.

    :param ctx: A :class:`ircdd.context.ConfigStore` object which contains both
    the raw config values and the initialized shared drivers.
    """
    protocol = IRCDDUser

    def __init__(self, ctx):
        # This is to support the stock IRCUser.
        # For other components, use ctx instead
        self.realm = ctx['realm']
        self.portal = ctx['portal']
        self._serverInfo = ctx['server_info']

        self.ctx = ctx


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

    irc_server = internet.TCPServer(int(ctx['port']), f)
    return irc_server


# In memory storage and checking of nicknames/passwords
# If user name is not found, it adds the user to the list
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
            # this may need to be changed if we use encrypted credentials
            self.users[credentials.username] = credentials.password
            return self.requestAvatarId(credentials)
