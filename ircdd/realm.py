from zope.interface import implements

from twisted.cred import portal
from twisted.words import ewords, iwords
from twisted.internet import defer
from twisted.python import failure, log

from ircdd.user import ShardedUser
from ircdd.group import ShardedGroup
from ircdd.protocol import ProxyIRCDDUser


class ShardedRealm(object):
    implements(portal.IRealm, iwords.IChatService)

    _encoding = "utf8"

    createUserOnRequest = True
    createGroupOnRequest = False

    """
    A realm which may exist in a sharded state across different
    servers. It works with :class:`ircdd.server.ShardedUser` and
    :class:`ircdd.server.ShardedGroup` and handles operations on those
    both for the local shard and the common state in the database.
    It represents both the local view of the cumulative realm state
    (all server nodes, everywhere) and the local scope (users connected
    to the local instance).
    It subscribes to groups on behalf of the locally connected users
    and performs message relaying to the latter.
    """
    def __init__(self, ctx, name):
        # The shard's name
        self.name = name

        self.ctx = ctx

        self.createUserOnRequest = ctx["user_on_request"]
        self.createGroupOnRequest = ctx["group_on_request"]

        self.users = {}

        # Groups contain proxies to groups that the local users are
        # interested in. The group state and meta found in the DB
        # are the authoritative versions of the data.
        # The local ShardedGroup serves as a local relay and cache.
        self.groups = {}

    def userFactory(self, name):
        return ShardedUser(self.ctx, name)

    def groupFactory(self, name):
        return ShardedGroup(self.ctx, name)

    def logoutFactory(self, avatar, facet):
        def logout():
            getattr(facet, "logout", lambda: None)()
            avatar.realm = avatar.mind = None

        return logout

    def requestAvatar(self, avatarId, mind, *interfaces):
        if isinstance(avatarId, str):
            avatarId = avatarId.decode(self._encoding)

        def gotAvatar(avatar):
            if avatar.realm is not None:
                raise ewords.AlreadyLoggedIn()

            for iface in interfaces:
                facet = iface(avatar, None)
                if facet is not None:
                    avatar.loggedIn(self, mind)
                    mind.name = avatarId
                    mind.realm = self
                    mind.avatar = avatar
                    return iface, facet, self.logoutFactory(avatar, facet)
            raise NotImplementedError(self, interfaces)
        return self.getUser(avatarId).addCallback(gotAvatar)

    def itergroups(self):
        # TODO: Integrate database.
        # Add a lookup for remote groups?
        return defer.succeed(self.groups.itervalues())

    def addUser(self, user):
        # TODO: Integrate database.
        # check straight in the DB's user list
        if user.name in self.users:
            return defer.fail(failure.Failure(ewords.DuplicateUser()))

        self.users[user.name] = user
        return defer.succeed(user)

    def addGroup(self, group):
        # TODO: Integrate database.
        if group.name in self.groups:
            return defer.fail(failure.Failure(ewords.DuplicateGroup()))

        self.groups[group.name] = group
        return defer.succeed(group)

    def lookupUser(self, name):
        """
        Looks for the given user first in the local store and
        failing that in the database. If found in the databse,
        checks the session for validity - if the session is valid
        the user must be connected to some other node, so a ShardedUser
        with a ProxyIRCDDUser for mind is returned. If the session is
        not valid, fail with NoSuchUser.
        """
        assert isinstance(name, unicode)
        name = name.lower()

        local_user = self.users.get(name)
        if local_user:
            return defer.succeed(local_user)

        remote_user = self.ctx.db.lookupUser(name)
        user_session = self.ctx.db.lookupUserSession(name)

        # User exists and session is active, so he must be
        # connected to some remote
        if remote_user and user_session:
            return defer.succeed(ShardedUser(self.ctx,
                                             name,
                                             ProxyIRCDDUser(self.ctx, name)))

        return defer.fail(failure.Failure(ewords.NoSuchUser(name)))

    def lookupGroup(self, name):
        # TODO: Integrate database.
        assert isinstance(name, unicode)
        name = name.lower()

        group = self.groups.get(name)
        if group:
            return defer.succeed(group)

        group = self.ctx.db.lookupGroup(name)
        if group:
            return defer.succeed(self.groupFactory(name))

        return defer.fail(failure.Failure(ewords.NoSuchGroup(name)))

    def getGroup(self, name):
        # TODO: Integrate database.
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
        # TODO: Integrate database.
        assert isinstance(name, unicode)

        if self.createUserOnRequest:
            def ebUser(err):
                err.trap(ewords.DuplicateUser)
                return self.lookupUser(name)
            return self.createUser(name).addErrback(ebUser)

        log.msg("Getting user %s" % name)
        return self.lookupUser(name)

    def createGroup(self, name):
        # TODO: Integrate database.
        assert isinstance(name, unicode)

        def cbLookup(group):
            return failure.Failure(ewords.DuplicateGroup(name))

        def ebLookup(err):
            err.trap(ewords.NoSuchGroup)
            self.ctx.db.createGroup(name, "public")
            return self.groupFactory(name)

        name = name.lower()

        d = self.lookupGroup(name)
        d.addCallbacks(cbLookup, ebLookup)
        d.addCallback(self.addGroup)

        log.msg("Creating group %s" % name)
        return d

    def createUser(self, name):
        # TODO: Integrate database.
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
