from twisted.words.service import IRCUser
from twisted.python import log
from twisted.words import iwords


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
