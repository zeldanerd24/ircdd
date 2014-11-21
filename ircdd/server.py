from time import time
from twisted.words.service import IRCUser, Group, User, WordsRealm
from twisted.application import internet
from twisted.internet import protocol, defer, task
from twisted.python import failure, log
from twisted.words import ewords, iwords


class ShardedUser(User):
    """
    A User which may exist in a sharded state on different IRC
    servers. It subscribes to its own topic on the message queue
    and sends/responds to remote messages.
    """
    def __init__(self, ctx, name):
        super(ShardedUser, self).__init__(name)
        self.ctx = ctx
        self.ctx["remote_rw"].subscribe(self.name, self.receiveRemote)

        self.heartbeat = task.LoopingCall(self._hbPresence)
        self.heartbeat_groups = task.LoopingCall(self._hbGroupPresence)

    def _hbPresence(self):
        self.ctx.db.heartbeatUserPresence(self.name)

    def _hbGroupPresence(self):
        for group in self.groups:
            self.ctx.db.heartbeatUserGroupPresence(self.name, group.name)

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

        self.mind.receive(parsed_msg["msg_body"]["sender"]["name"],
                          self, parsed_msg["msg_body"])

        message.finish()

    def loggedIn(self, realm, mind):
        super(ShardedUser, self).loggedIn(realm, mind)

        self._hbPresence()

        self.heartbeat.start(10.0)
        self.heartbeat_groups.start(10.0)

    def logout(self):
        self.heartbeat.stop()
        self.heartbeat_groups.stop()

        for g in self.groups:
            self.leave(g)

        self.ctx.db.removeUserPresence(self.name)

    def join(self, group):
        def cbJoin(result):
            self.groups.append(group)
            self._hbGroupPresence()
            return result

        return group.add(self.mind).addCallback(cbJoin)

    def leave(self, group, reason=None):
        def cbLeave(result):
            self.groups.remove(group)
            self.ctx.db.removeUserGroupPresence(self.name, group.name)

        return group.remove(self.mind, reason).addCallback(cbLeave)


class ShardedGroup(Group):
    """
    A group which may exist in a sharded state on different
    servers. It subscribes to its own topic on the message queue
    and sends/receives remote messages.
    """
    def __init__(self, ctx, name):
        super(ShardedGroup, self).__init__(name)
        self.ctx = ctx
        self.ctx.remote_rw.subscribe(self.name, self.receiveRemote)

    def _observeSharedPresence(self):
        for change in self.ctx.db.observePresenceInGroup(self.name):
            log.msg("Change %s" % str(change))

    def receiveRemote(self, message):
        """
        Callback which is executed when the Reader for this group's
        topic receives a message.

        :param message: A :class:`nsq.Message` which contains
        the IRC message and metadata in its parsed_body.
        """
        parsed_msg = message.parsed_msg
        self.receive(parsed_msg["msg_body"]["sender"],
                     self,
                     parsed_msg.get("msg_body", None))
        message.finish()

    def receive(self, sender_name, recipient, message):
        assert recipient is self
        recipients = []

        for recipient in self.users.itervalues():
            if recipient.name != sender_name:
                d = defer.maybeDeferred(recipient.receive, sender_name,
                                        self.name, message)
                d.addErrback(self._ebUserCall, p=recipient)
                recipients.append(d)
        defer.DeferredList(recipients).addCallback(self._cbUserCall)
        return defer.succeed(None)


class ShardedRealm(WordsRealm):
    """
    A realm which may exist in a sharded state on different
    servers. It works with :class:`ircdd.server.ShardedUser` and
    :class:`ircdd.server.ShardedGroup` and handles operations on those
    both for the local shard and the common state in the database.
    """
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
        # TODO: Integrate database.
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
        # This is an ugly hack and needs to be fixed. Maybe
        # defining some serializable "shell" IRCUser that can
        # be passed around with the NSQ messages?

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
