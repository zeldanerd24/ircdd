from zope.interface import implements

from twisted.words import iwords
from twisted.internet import defer, reactor, threads
from twisted.python import failure, log


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

        self.getMeta()
        self.getState()

        threads.deferToThread(self._observeMeta)
        threads.deferToThread(self._observeState)

    def _ebUserCall(self, err, p):
        return failure.Failure(Exception(p, err))

    def _cbUserCall(self, results):
        for (success, result) in results:
            if not success:
                user, err = result.value
                self.remove(user, err.getErrorMessage())

    def getMeta(self):
        """
        Gets the group's metadata from `RDB` and
        populates the local structure with it.
        """
        group = self.ctx.db.lookupGroup(self.name)
        if group:
            self.updateMeta(group["meta"])

    def getState(self):
        """
        Gets the groups state from `RDB` and
        populates the local shard with it.
        """
        state = self.ctx.db.getGroupState(self.name)
        if state:
            self.users = state["users"]

    def _observeState(self):
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

        def updateUserList(users):
            self.users = users

        for change in changeset:
            reactor.callFromThread(updateUserList,
                                   change["users"])

    def _observeMeta(self):
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
                reactor.callFromThread(self.updateMeta,
                                       change["new_val"]["meta"])

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
            self.notifyAdd(added_user.name, added_user.ctx.hostname)
            self.notifyShardsAdd(added_user.name)

        return defer.succeed(None)

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

    def receiveRemote(self, message):
        """
        Callback which is executed when the Reader for this group's
        topic receives a message.

        :param message: A :class:`nsq.Message` which contains
        the IRC message and metadata in its parsed_body.
        """
        msg_body = message.parsed_msg["msg_body"]
        msg_type = msg_body["type"]

        if msg_type == "privmsg":
            self.receive(msg_body["sender"]["name"],
                         self,
                         msg_body)
        elif msg_type == "join":
            self.notifyAdd(msg_body["sender"]["name"],
                           msg_body["sender"]["hostname"])
        elif msg_type == "part":
            self.notifyRemove(msg_body["sender"]["name"],
                              msg_body["reason"])

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
        """
        Returns the list of users connected to this
        group across all instances.
        """
        return iter(self.users)

    def setMetadata(self, meta):
        """
        Attempts to set the group meta in RDB.
        If successful, the local meta will be set via the
        observer thread.
        """
        self.ctx.db.setGroupTopic(self.name,
                                  meta["topic"],
                                  meta["topic_author"])

        return defer.succeed(None)

    def updateMeta(self, meta):
        """
        Updates the local instance's meta
        """
        self.meta = meta
        self.notifyMetaChange()
        return defer.succeed(None)

    def notifyMetaChange(self):
        sets = []
        # Maybe dispatch this on NSQ to notify the rest?
        # Or just make it happen on the observation thread.
        # Either way should not be here.
        for user in self.local_sessions.itervalues():
            d = defer.maybeDeferred(user.groupMetaUpdate, self, self.meta)
            d.addErrback(self._ebUserCall, p=user)
            sets.append(d)
        defer.DeferredList(sets).addCallback(self._cbUserCall)
        return defer.succeed(None)

    def notifyShardsAdd(self, added_user_name):
        """
        Submits a `join` message on this group's topic,
        notifying remote shards of the event so that they
        can in turn relay it to their users.
        """
        message = {
            "type": "join",
            "sender": {
                "name": added_user_name,
                "hostname": self.ctx.hostname,
                }
            }
        self.ctx.remote_rw.publish(self.name, message)

    def notifyAdd(self, added_user_name, added_user_hostname):
        """
        Notify the local users of a `join` event.
        """
        additions = []

        for user in self.local_sessions.itervalues():
            if user.name != added_user_name:
                d = defer.maybeDeferred(user.userJoined, self,
                                        added_user_name, added_user_hostname)
                d.addErrback(self._ebUserCall, p=user)
                additions.append(d)
        defer.DeferredList(additions).addCallback(self._cbUserCall)

    def notifyRemove(self, removed_user_name, reason="unknown reason"):
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

    def notifyShardsRemove(self, removed_user_name, reason="unknown reason"):
        """
        Publishes a `part` message to this group's topic in order to
        notify other instances if the event.
        """
        message = {
            "type": "part",
            "sender": {
                "name": removed_user_name,
                "hostname": self.ctx.hostname,
            },
            "reason": reason
        }
        self.ctx.remote_rw.publish(self.name, message)

    def size(self):
        return defer.succeed(len(self.local_sessions))
