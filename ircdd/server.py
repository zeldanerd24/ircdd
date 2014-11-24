from time import time

from zope.interface import implements

from twisted.words import ewords, iwords
from twisted.words.service import IRCUser
from twisted.application import internet
from twisted.internet import protocol, defer, task, reactor, threads
from twisted.python import failure, log
from twisted.cred import portal


class ShardedUser(object):
    implements(iwords.IUser)
    mind = None
    realm = None

    """
    A User which may exist in a sharded state on different IRC
    servers. It subscribes to its own topic on the message queue
    and sends/responds to remote messages.
    """
    def __init__(self, ctx, name, mind=None):
        self.name = name
        self.groups = []
        self.lastMessage = time()
        self.mind = mind

        self.ctx = ctx
        self.ctx["remote_rw"].subscribe(self.name, self.receiveRemote)

        self.heartbeat = task.LoopingCall(self._hbSession)
        self.heartbeat_groups = task.LoopingCall(self._hbGroupSession)

    def _hbSession(self):
        """
        Sends a hearbeat to the user's session document.
        """
        self.ctx.db.heartbeatUserSession(self.name)

    def _hbGroupSession(self):
        """
        Sends heartbeats to all the groups that this user is a part of
        in order to maintain presence in them.
        """
        for group in self.groups:
            self.ctx.db.heartbeatUserInGroup(self.name, group.name)

    def send(self, recipient, message):
        """
        Sends message to the given recipient, even if the
        recipient is not local.
        Sending is done in four steps:
            1. Determine that recipient exists via the
            database.
            2. Dispatch message to the recipient's
            message topic.
            3. Add message to the database chat log.
            4. Dispatch message to the local shard of the
            recipient, if any.

        :param recipient: the IRCUser/Group to send to.
        :param message: the message to send.
        """

        message["sender"] = dict(name=self.name, hostname=self.ctx["hostname"])
        message["recipient"] = recipient.name
        message["type"] = "privmsg"

        self.ctx.remote_rw.publish(recipient.name, message)
        self.lastMessage = time()
        return recipient.receive(self.name, recipient, message)

    def receiveRemote(self, message):
        """
        Callback which is executed when the Reader for this user's
        topic receives a message.

        :param message: A :class:`nsq.Message` which
        contains the IRC message and metadata in its parsed body.
        """
        parsed_msg = message.parsed_msg
        msg_type = parsed_msg["msg_body"]["type"]

        if msg_type == "privmsg":
            self.mind.receive(parsed_msg["msg_body"]["sender"]["name"],
                              self, parsed_msg["msg_body"])

        message.finish()

    def loggedIn(self, realm, mind):
        """
        Associates this ShardedUser with a client connection
        and starts to heartbeat the user's session and group
        subscription,
        completing the login process.
        """
        self.realm = realm
        self.mind = mind
        self.signOn = time()

        self._hbSession()

        self.heartbeat.start(10.0)
        self.heartbeat_groups.start(10.0)

    def logout(self):
        """
        Stops maintaining the sessions and cleans them,
        completing the logout process
        """
        self.heartbeat.stop()
        self.heartbeat_groups.stop()

        for g in self.groups:
            self.leave(g)

        self.ctx.db.removeUserSession(self.name)

    def join(self, group):
        """
        Joins the desired group (if possible) and
        adds this user session to the group's
        users.
        """
        def cbJoin(result):
            self.groups.append(group)
            self._hbGroupSession()
            return result

        return group.add(self.mind).addCallback(cbJoin)

    def leave(self, group, reason=None):
        """
        Leaves the group, stops maintaining presence in it, and
        cleans out the session.
        """
        def cbLeave(result):
            self.groups.remove(group)
            self.ctx.db.removeUserFromGroup(self.name, group.name)

        return group.remove(self.mind, reason).addCallback(cbLeave)


class ShardedGroup(object):
    implements(iwords.IGroup)

    """
    A group which may exist in a sharded state on different
    servers. It subscribes to its own topic on the message queue
    and sends/receives remote messages.
    """
    def __init__(self, ctx, name):
        self.name = name
        self.users = {}
        self.local_sessions = {}
        self.meta = {"topic": "", "topic_author": ""}

        self.ctx = ctx
        self.ctx.remote_rw.subscribe(self.name, self.receiveRemote)

        self.getGroupMeta()
        self.getGroupState()

        threads.deferToThread(self._observeGroupMeta)
        threads.deferToThread(self._observeGroupState)

    def _ebUserCall(self, err, p):
        return failure.Failure(Exception(p, err))

    def _cbUserCall(self, results):
        for (success, result) in results:
            if not success:
                user, err = result.value
                self.remove(user, err.getErrorMessage())

    def getGroupMeta(self):
        """
        Gets the group's metadata from `RDB` and
        populates the local structure with it.
        """
        meta = self.ctx.db.lookupGroup(self.name)
        if meta:
            self.meta = meta["topic"]

    def getGroupState(self):
        """
        Gets the groups state from `RDB` and
        populates the local shard with it.
        """
        state = self.ctx.db.getGroupState(self.name)
        if state:
            self.users = state["user_heartbeats"]

    def _observeGroupState(self):
        """
        Continuously processes the stream of changes
        to the group's state.
        In order to join with the reactor thread on
        SIGINT, a callback forcefully closes the
        changeset's connection.
        """
        changeset = self.ctx.db.observeGroupState(self.name)

        reactor.addSystemEventTrigger("before", "shutdown",
                                      changeset.conn.close,
                                      False)
        for change in changeset:
            self.users = change["new_val"]["user_heartbeats"]

    def _observeGroupMeta(self):
        """
        Continuously processes the stream of changes to the
        group's metadata.
        In order to join with the reactor thread on SIGINT
        a callback forcefully closes the changeset's connection.
        """
        changeset = self.ctx.db.observeGroupMeta(self.name)

        reactor.addSystemEventTrigger("before", "shutdown",
                                      changeset.conn.close,
                                      False)
        for change in changeset:
            if change.get("new_val"):
                self.meta = {
                    "topic": change["new_val"]["topic"],
                    "topic_author": change["new_val"]["topic_author"]
                }

    def add(self, added_user):
        """
        Adds a user to this shard as a local session.
        Notifies all other active local users and posts a
        message on the group's topic to notify remote users.
        """
        assert iwords.IChatClient.providedBy(added_user), \
            "%r is not a chat client" % (added_user,)

        if added_user.name not in self.local_sessions:
            self.local_sessions[added_user.name] = added_user
            self.notifyAdd(added_user)
            self.notifyShardsAdd(added_user.name)

        return defer.succeed(None)

    def notifyShardsAdd(self, added_user_name):
        """
        Submits a `join` message on this group's topic,
        notifying remote shards of the event so that they
        can in turn relay it to their users.
        """
        message = {"type": "join", "user": added_user_name}
        self.ctx.remote_rw.publish(self.name, message)

    def notifyAdd(self, added_user):
        """
        Notify the local users of a `join` event.
        """
        additions = []
        for user in self.local_sessions.itervalues():
            if user.name != added_user.name:
                d = defer.maybeDeferred(user.userJoined, self, added_user)
                d.addErrback(self._ebUserCall, p=user)
                additions.append(d)
        defer.DeferredList(additions).addCallback(self._cbUserCall)

    def remove(self, removed_user, reason=None):
        """
        Remove a local user from the group.
        """
        assert reason is None or isinstance(reason, unicode)

        try:
            del self.local_sessions[removed_user.name]
        except KeyError:
            log.err("Removing user %s failed: user does not exist" %
                    removed_user.name)
        else:
            self.notifyRemove(removed_user.name, reason)
            self.notifyShardsRemove(removed_user.name, reason)
        return defer.succeed(None)

    def notifyRemove(self, removed_user_name, reason=None):
        """
        Notify the local users of a `part` event.
        """
        removals = []
        for user in self.local_sessions.itervalues():
            if user.name != removed_user_name:
                d = defer.maybeDeferred(user.userLeft,
                                        self,
                                        removed_user_name,
                                        reason)
                d.addErrback(self._ebUserCall, p=user)
                removals.append(d)
        defer.DeferredList(removals).addCallback(self._cbUserCall)

    def notifyShardsRemove(self, removed_user_name, reason=None):
        message = {
            "type": "part",
            "user": {
                "name": removed_user_name,
                "hostname": self.ctx.hostname
            },
            "reason": reason
        }
        self.ctx.remote_rw.publish(self.name, message)

    def receiveRemote(self, message):
        """
        Callback which is executed when the Reader for this group's
        topic receives a message.

        :param message: A :class:`nsq.Message` which contains
        the IRC message and metadata in its parsed_body.
        """
        parsed_msg = message.parsed_msg
        msg_type = parsed_msg["msg_body"]["type"]

        if msg_type == "privmsg":
            self.receive(parsed_msg["msg_body"]["sender"],
                         self,
                         parsed_msg.get("msg_body", None))
        elif msg_type == "join":
            self.notifyAdd(parsed_msg["user"])
        elif msg_type == "part":
            self.notifyRemove(parsed_msg["user"], parsed_msg["reason"])

        message.finish()

    def receive(self, sender_name, recipient, message):
        """
        Multicasts the message to all local users.
        """
        assert recipient is self
        recipients = []

        for recipient in self.local_sessions.itervalues():
            if recipient.name != sender_name:
                d = defer.maybeDeferred(recipient.receive, sender_name,
                                        self, message)
                d.addErrback(self._ebUserCall, p=recipient)
                recipients.append(d)
        defer.DeferredList(recipients).addCallback(self._cbUserCall)
        return defer.succeed(None)

    def iterusers(self):
        return iter(self.local_sessions.values())

    def setMetadata(self, meta):
        self.ctx.db.setGroupMeta(self.name, meta)

        self.meta = meta

        sets = []

        for user in self.local_sessions.itervalues():
            d = defer.maybeDeferred(user.groupMetaUpdate, self, meta)
            d.addErrback(self._ebUserCall, p=user)
            sets.append(d)
        defer.DeferredList(sets).addCallback(self._cbUserCall)
        return defer.succeed(None)

    def size(self):
        return defer.succeed(len(self.local_sessions))


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


class ProxyIRCDDUser():
    """
    Shell object that stands in place of a real client connection.
    It is used when the lcoal node must operate on a ShardedUser
    which is connected to a different node.
    """
    def __init__(self, ctx, name):
        self.ctx = ctx
        self.name = name

    def receive(self, sender_name, recipient, message):
        """
        The remote client will process the message via NSQ, so this
        method just logs the fact that the proxy was hit.
        """
        log.msg("Proxy received message %s" % str(message))


class IRCDDUser(IRCUser):
    def receive(self, sender_name, recipient, message):
        """
        Receives a message from the sender for the given recipient.

        :param sender: Who is sending the message.
        :param recipient: Who is receiving the message; not neccessarily
        this IRCUser.
        :param message: A message dictionary. If remote, the message will
        contain additional metadata.
        """
        # This is an ugly hack from the Twisted codebase.
        # No idea why it has to be like this but I am too scared
        # to try and fix it
        if iwords.IGroup.providedBy(recipient):
            recipient_name = "#" + recipient.name
        else:
            recipient_name = recipient.name

        text = message.get("text", "<an unrepresentable message>")

        for L in text.splitlines():
            self.privmsg("%s!%s@%s" % (sender_name,
                                       sender_name,
                                       self.hostname),
                         recipient_name, L)

    def userJoined(self, group, user):
        # Stupid workaround the fact that this method expects (and receives)
        # the FULL IRCUser object, even though it clearly needs
        # only the username... So in order to pass it the username
        # from a remote message, it has to also handle reciving dicts.
        if isinstance(user, dict):
            user_name = user["name"]
            user_hostname = user["hostname"]
        else:
            user_name = user.name
            user_hostname = user.hostname
        self.join(
            "%s!%s@%s" % (user_name, user_name, user_hostname),
            "#" + group.name)


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
