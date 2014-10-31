from zope.interface import implements
from twisted.words.service import IRCUser, Group, User, WordsRealm
from twisted.application import internet
from twisted.internet import protocol, defer
from twisted.python import failure, log
from twisted.cred import checkers, error, credentials
from twisted.words import ewords


class ShardedUser(User):
    def __init__(self, ctx, name):
        super(ShardedUser, self).__init__(name)
        self.ctx = ctx
        self.ctx["remote_rw"].subscribe(self.name, self.receiveRemote)

    def send(self, recipient, message):
        if isinstance(recipient, IRCUser):
            recipient_name = recipient.nickname
        else:
            recipient_name = recipient.name

        message["sender"] = self.name
        message["recipient"] = recipient_name

        self.ctx["remote_rw"].publish(recipient_name, message)
        super(ShardedUser, self).send(recipient, message)

    def receiveRemote(self, message):
        # sender only contains a "name" attribute
        sender = message.sender
        self.mind.receive(sender, self, message)


class ShardedGroup(Group):
    def __init__(self, ctx, name):
        super(ShardedGroup, self).__init__(name)
        self.ctx = ctx
        self.ctx["remote_rw"].subscribe(self.name, self.receiveRemote)

    def receiveRemote(self, message):
        body = message["msg_body"]
        super(ShardedGroup, self).receive(body["sender"],
                                          self,
                                          body["text"])
        message.finish()


class ShardedRealm(WordsRealm):
    def __init__(self, ctx, *a, **kw):
        super(ShardedRealm, self).__init__(*a, **kw)
        self.ctx = ctx
        self.createUserOnRequest = ctx["user_on_request"]
        self.createGroupOnRequest = ctx["group_on_request"]
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

        # lookup in self, then database.
        # if found in database but not self,
        # create in db and add to self before returning
        try:
            group = self.groups[name]
        except KeyError:
            return defer.fail(failure.Failure(ewords.NoSuchGroup(name)))
        else:
            return defer.succeed(group)

    def getGroup(self, name):
        assert isinstance(name, unicode)

        # Get this setting from the cluster's policy
        if self.createGroupOnRequest:
            def ebGroup(err):
                err.trap(ewords.DuplicateGroup)
                return self.lookupGroup(name)
            return self.createGroup(name).addErrback(ebGroup)

        log.msg("Getting group %s" % name)
        return self.lookupGroup(name)

    def getUser(self, name):
        assert isinstance(name, unicode)

        if self.createUserOnRequest:
            def ebUser(err):
                err.trap(ewords.DuplicateUser)
                return self.lookupUser(name)
            return self.createUser(name).addErrback(ebUser)

        log.msg("Getting user %s" % name)
        return self.lookupUser(name)

    def createGroup(self, name):
        assert isinstance(name, unicode)

        def cbLookup(group):
            return failure.Failure(ewords.DuplicateGroup(name))

        def ebLookup(err):
            err.trap(ewords.NoSuchGroup)
            return self.groupFactory(name)

        name = name.lower()

        d = self.lookupGroup(name)
        d.addCallbacks(cbLookup, ebLookup)
        d.addCallback(self.addGroup)

        log.msg("Creating group %s" % name)
        return d

    def createUser(self, name):
        assert isinstance(name, unicode)

        def cbLookup(user):
            return failure.Failure(ewords.DuplicateUser(name))

        def ebLookup(err):
            err.trap(ewords.NoSuchUser)
            return self.userFactory(name)

        name = name.lower()

        d = self.lookupUser(name)
        d.addCallbacks(cbLookup, ebLookup)
        d.addCallback(self.addUser)

        log.msg("Creating user %s" % name)
        return d


class IRCDDFactory(protocol.ServerFactory):
    """
    Factory which creates instances of the :class:`ircdd.server.IRCDDUser`
    protocol. Expects to receive an initialized context object at creation.

    :param ctx: A :class:`ircdd.context.ConfigStore` object which contains both
    the raw config values and the initialized shared drivers.
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
