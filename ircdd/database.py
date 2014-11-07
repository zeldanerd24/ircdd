import rethinkdb as r
from twisted.python import log


class IRCDDatabase:
    """
    Wrapper class for database actions, so that the IRC server
    does not have to know anything about how rethinkDB works
    in order to use it
    """

    USERS_TABLE = 'users'
    GROUPS_TABLE = 'groups'

    def __init__(self, db="ircdd", host="127.0.0.1", port=28015):
        self.rdb_host = host
        self.rdb_port = port
        self.db = db
        self.conn = r.connect(db=self.db,
                              host=self.rdb_host,
                              port=self.rdb_port)

    def createUser(self, nickname,
                   email="", password="", registered=False, permissions={}):
        """
        Add a user to the user table
        User table has the following fields:
        nickname (string), email (string), password (string),
        registered (boolean), permissions (dict of channel name: permissions
        contains channel name (string) and permissions (string))
        """

        exists = r.table(self.USERS_TABLE).get(
            nickname
            ).run(self.conn)

        if not exists:
            r.table(self.USERS_TABLE).insert({
                "id": nickname,
                "nickname": nickname,
                "email": email,
                "password": password,
                "registered": registered,
                "permissions": permissions
            }).run(self.conn)
        else:
            log.err("User already exists: %s" % nickname)

    def lookupUser(self, nickname):
        """
        Finds the user with given nickname and returns the dict for it
        Returns None if the user is not found
        """
        return r.table(self.USERS_TABLE).get(
            nickname
            ).run(self.conn)

    def registerUser(self, nickname, email, password):
        """
        Finds unregistered user with same nickname and registers them with
        the given email, password, and sets registered to True
        """
        assert email
        assert password

        result = r.table(self.USERS_TABLE).filter({
            "nickname": nickname
            }).update({
                "email": email,
                "password": password,
                "registered": True
            }).run(self.conn)
        return result

    def deleteUser(self, nickname):
        """
        Find and delete the user given by nickname
        """

        return r.table(self.USERS_TABLE).get(
            nickname
            ).delete().run(self.conn)

    def setPermission(self, nickname, channel, permission):
        """
        Set permission for user for the given channel to the permissions string
        defined by permission
        """
        current_permissions = r.table(self.USERS_TABLE).get(
            nickname
            ).pluck("permissions").run(self.conn)

        permissions_for_channel = current_permissions.get(channel, [])
        permissions_for_channel.append(permission)

        return r.table(self.USERS_TABLE).get(
            nickname
            ).update({
                "permissions": r.row["permissions"].merge({
                    channel: permissions_for_channel
                    })
            }).run(self.conn)

    def createGroup(self, name, owner, channelType):
        """
        Create an IRC channel (if it doesn't exist yet) in the channels table
        Fields for the channels table are:
        name (string) the name of the channel
        owner (string) the owner (by nickname) of the channel
        type (string) public or private
        topic (dict) dict of topic message, topic author, topic time
        messages (array of dicts) each element (message) contains
        message time, message author, and message contents
        """
        assert name
        assert owner
        assert channelType

        exists = r.table(self.GROUPS_TABLE).get(
            name
            ).run(self.conn)

        if not exists:
            r.table(self.GROUPS_TABLE).insert({
                "id": name,
                "name": name,
                "owner": owner,
                "type": channelType,
                "topic": {},
                "messages": []
            }).run(self.conn)
        else:
            log.err("Group already exists: %s" % name)

    def lookupGroup(self, name):
        """
        Return the IRC channel dict for channel with given name
        """

        return r.table(self.GROUPS_TABLE).get(
            name
            ).run(self.conn)

    def listGroups(self):
        """
        Returns an array of all IRC channel names present in the database
        """

        return list(r.table(self.CHANNEL_TABLE).pluck("name").run(self.conn))

    def deleteGroup(self, name):
        """
        Delete the IRC channel with the given channel name
        """

        return r.table(self.GROUPS_TABLE).get(
            name
            ).delete().run(self.conn)

    def setGroupTopic(self, name, topic, topic_time, author):
        """
        Set the IRC channel's topic
        """

        r.table(self.GROUPS_TABLE).get(name).update({
            "topic": {
                "topic": topic,
                "topic_time": topic_time,
                "topic_author": author
                }
            }).run(self.conn)

    def addMessage(self, name, sender, time, text):
        """
        Add a message to IRC channel denoted by channel_name, written by
        nickname and store the message time and contents
        """

        r.table(self.GROUPS_TABLE).get(name).update({
            "messages": r.row["messages"].append({
                "sender": sender,
                "time": time,
                "text": text
                })
            }).run(self.conn)
