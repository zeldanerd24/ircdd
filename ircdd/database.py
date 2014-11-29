import re
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
    USER_SESSIONS_TABLE = 'user_sessions'
    GROUP_STATES_TABLE = 'group_states'

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

    def heartbeatUserSession(self, nickname):
        session = r.table(self.USER_SESSIONS_TABLE).get(
            nickname
        ).run(self.conn)

        if not session:
            return r.table(self.USER_SESSIONS_TABLE).insert({
                "id": nickname,
                "last_heartbeat": r.now(),
                "last_message": r.now(),
                "session_start": r.now()
            }).run(self.conn)
        else:
            return r.table(self.USER_SESSIONS_TABLE).get(nickname).update({
                "last_heartbeat": r.now()
            }).run(self.conn)

    def removeUserSession(self, nickname):
        return r.table(self.USER_SESSIONS_TABLE).get(
            nickname
        ).delete().run(self.conn)

    def removeUserFromGroup(self, nickname, group):
        return r.table(self.GROUP_STATES_TABLE).get(group).replace(
            r.row.without({"users": {nickname: True}})
        ).run(self.conn)

    def heartbeatUserInGroup(self, nickname, group):
        presence = r.table(self.GROUP_STATES_TABLE).get(
            group
        ).run(self.conn)

        if not presence:
            return r.table(self.GROUP_STATES_TABLE).insert({
                "id": group,
                "users": {
                    nickname: r.now()
                }
            }).run(self.conn)
        else:
            return r.table(self.GROUP_STATES_TABLE).get(group).update({
                "users": r.row["users"].merge({
                    nickname: r.now()
                })
            }).run(self.conn)

    def observeGroupState(self, group):
        conn = r.connect(db=self.db,
                         host=self.rdb_host,
                         port=self.rdb_port)

        return r.table(self.GROUP_STATES_TABLE).changes().filter(
            r.row["old_val"]["id"] == group or r.row["new_val"]["id"] == group
        ).run(conn)

    def observeGroupMeta(self, group):
        conn = r.connect(db=self.db,
                         host=self.rdb_host,
                         port=self.rdb_port)

        return r.table(self.GROUPS_TABLE).changes().filter(
            r.row["old_val"]["id"] == group or r.row["new_val"]["id"] == group
        ).run(conn)

    def lookupUser(self, nickname):
        """
        Finds the user with given nickname and returns the dict for it
        Returns None if the user is not found
        """
        exists = r.table(self.USERS_TABLE).get(
            nickname
        ).run(self.conn)

        if exists:
            return r.table(self.USERS_TABLE).get(
                nickname
            ).merge({
                "session": r.table(self.USER_SESSIONS_TABLE).get(nickname),
                "groups": r.table(self.GROUPS_TABLE).filter(
                    lambda group: r.table(self.GROUP_STATES_TABLE)
                                   .get(group["id"])
                                   .has_fields({
                                       "users": {
                                           nickname: True
                                       }
                                   })
                ).coerce_to("array")
            }).run(self.conn)
        else:
            return None

    def lookupUserSession(self, nickname):
        return r.table(self.USER_SESSIONS_TABLE).get(
            nickname
        ).run(self.conn)

    def registerUser(self, nickname, email, password):
        """
        Finds unregistered user with same nickname and registers them with
        the given email, password, and sets registered to True
        """

        self.checkIfValidEmail(email)
        self.checkIfValidNickname(nickname)
        self.checkIfValidPassword(password)

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

    def createGroup(self, name, channelType):
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
        assert channelType

        exists = r.table(self.GROUPS_TABLE).get(
            name
            ).run(self.conn)

        if not exists:
            group = r.table(self.GROUPS_TABLE).insert({
                "id": name,
                "name": name,
                "type": channelType,
                "meta": {
                    "topic": "",
                    "topic_author": "",
                    "topic_time": r.now()
                },
                "messages": []
            }).run(self.conn)

            state = r.table(self.GROUP_STATES_TABLE).insert({
                "id": name,
                "users": {}
            }).run(self.conn)

            return group, state
        else:
            log.err("Group already exists: %s" % name)

    def lookupGroup(self, name):
        """
        Return the IRC channel dict for channel with given name,
        along with the merged state data.
        """
        group = r.table(self.GROUPS_TABLE).get(
            name
        ).run(self.conn)

        if group:
            return r.table(self.GROUPS_TABLE).get(
                name
            ).merge({
                "users": r.table(self.GROUP_STATES_TABLE)
                          .get(name)["users"]
            }).run(self.conn)
        else:
            return None

    def getGroupState(self, name):
        return r.table(self.GROUP_STATES_TABLE).get(
            name
        ).run(self.conn)

    def listGroups(self):
        """
        Returns a list of all groups. The documents in the list
        contain both the current metadata (name, topic, etc) and
        state information (user sessions).
        """

        return list(r.table(self.GROUPS_TABLE).filter(
            {"type": "public"}
        ).merge(lambda group: {
            "users": r.table(self.GROUP_STATES_TABLE)
                      .get(group["id"])["users"]
        }).run(self.conn))

    def deleteGroup(self, name):
        """
        Delete the IRC channel with the given channel name
        """

        deleted_group = r.table(self.GROUPS_TABLE).get(
            name
        ).delete().run(self.conn)

        deleted_state = r.table(self.GROUP_STATES_TABLE).get(
            name
        ).delete().run(self.conn)

        return deleted_group, deleted_state

    def setGroupTopic(self, name, topic, author):
        """
        Set the IRC channel's topic
        """

        return r.table(self.GROUPS_TABLE).get(name).update({
            "meta": {
                "topic": topic,
                "topic_time": r.now(),
                "topic_author": author
                }
            }).run(self.conn)

    def addMessage(self, name, sender, text):
        """
        Add a message to IRC channel denoted by channel_name, written by
        nickname and store the message time and contents
        """

        r.table(self.GROUPS_TABLE).get(name).update({
            "messages": r.row["messages"].append({
                "sender": sender,
                "time": r.now(),
                "text": text
                })
            }).run(self.conn)

    def checkIfValidEmail(self, email):
        """
        Checks if the passed email is valid based on the regex string
        """

        valid_email = re.compile(
            r"(^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$)")

        if not valid_email.match(email):
            log.error("Invalid email: %s" % email)
            raise ValueError(email)

    def checkIfValidNickname(self, nickname):
        """
        Checks if the passed nickname is valid based on the regex string
        """

        min_len = 3
        max_len = 64

        valid_nickname = re.compile(
            r"^(?i)[a-z0-9_-]{%s,%s}$" % (min_len, max_len))

        if not valid_nickname.match(nickname):
            log.error("Invalid nick: %s" % nickname)
            raise ValueError(nickname)

    def checkIfValidPassword(self, password):
        """
        Checks if the passed password is valid based on the regex string
        """

        min_len = 6
        max_len = 64

        valid_password = re.compile(
            r"^(?i)[a-z0-9_-]{%s,%s}$" % (min_len, max_len))

        if not valid_password.match(password):
            log.error("Invalid password: %s" % password)
            raise ValueError(password)

    def privateMessage(self, sender, receiver, time, message):
        """
        Creates an IRC channel for private messages between two users.
        The channel_name is the alphabetical ordering of the user's
        nicknames separated by a ':'
        """

        list = [sender, receiver]
        list.sort()

        name = list[0] + ":" + list[1]

        if not self.lookupGroup(name):
            self.createGroup(name, 'private')

        self.addMessage(name, sender, time, message)
