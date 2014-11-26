from twisted.words.service import IRCUser
from twisted.python import log
from twisted.words import iwords, ewords
from twisted.words.protocols import irc


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
        log.msg("Proxy received message %s from %s for %s" %
                str(message, sender_name, recipient))


class IRCDDUser(IRCUser):
    password = "no password"

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

    def userLeft(self, group, user_name, reason=None):
        assert reason is None or isinstance(reason, unicode)

        self.part(
            "%s!%s@%s" % (user_name, user_name, self.hostname),
            '#' + group.name,
            (reason or u"leaving").encode(self.encoding, 'replace'))

    def irc_JOIN(self, prefix, params):
        try:
            groupName = params[0].decode(self.encoding)
        except UnicodeDecodeError:
            self.sendMessage(
                irc.ERR_NOSUCHCHANNEL, params[0],
                ":No such channel (could not decode your unicode!)")
            return

        # Why on earth is this getting stripped from the
        # group name?!
        if groupName.startswith("#"):
            groupName = groupName[1:]

        def cbGroup(group):
            def cbJoin(ign):
                self.userJoined(group, self)
                self.names(
                    self.name,
                    "#" + groupName,
                    group.iterusers())
                self._sendTopic(group)
            return self.avatar.join(group).addCallback(cbJoin)

        def ebGroup(err):
            self.sendMessage(
                irc.ERR_NOSUCHCHANNEL, "#" + groupName,
                ":No such channel.")

        self.realm.getGroup(groupName).addCallbacks(cbGroup, ebGroup)

    def irc_NAMES(self, prefix, params):
        try:
            groupName = params[-1].decode(self.encoding)
        except UnicodeDecodeError:
            self.sendMessage(
                irc.ERR_NOSUCHCHANNEL, params[0],
                ":No such channel (could not decode your unicode!)")
            return

        if groupName.startswith("#"):
            groupName = groupName[1:]

        def cbGroup(group):
            self.userJoined(group, self)
            self.names(
                self.name,
                "#" + groupName,
                group.iterusers())
            self._sendTopic(group)

        def ebGroup(err):
            err.trap(ewords.NoSuchGroup)
            self.names(
                self.name,
                "#" + groupName,
                [])
        self.realmlookupGroup(groupName).addCallbacks(cbGroup, ebGroup)

    def _channelWho(self, group):
        self.who(self.name, "#" + group.name,
                 [(user, self.hostname, self.realm.name, user, "H", 0, user)
                  for user in group.iterusers()])
