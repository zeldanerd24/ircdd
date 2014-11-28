from time import time

from zope.interface import implements

from twisted.words import iwords
from twisted.internet import task


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
