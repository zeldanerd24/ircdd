import rethinkdb as r
from ircdd import database

from ircdd.tests import integration


class TestIRCDDatabase():
    def setUp(self):
        self.conn = r.connect(db=integration.DB,
                              host=integration.HOST,
                              port=integration.PORT)

        integration.createTables()

        self.db = database.IRCDDatabase(integration.DB,
                                        integration.HOST,
                                        integration.PORT)

    def tearDown(self):
        integration.dropTables()

        self.conn.close()

        self.db.conn.close()
        self.db = None

    def test_createUser(self):
        self.db.createUser('test_user',
                           email='user@test.dom',
                           password='password',
                           registered=True)
        user = self.db.lookupUser('test_user')
        assert user['nickname'] == "test_user"
        assert user['email'] == 'user@test.dom'
        assert user['password'] == 'password'
        assert user['registered']
        assert user['permissions'] == {}

    def test_registerUser(self):
        self.db.createUser('test_user')

        user = self.db.lookupUser('test_user')
        assert user['nickname'] == 'test_user'
        assert user['email'] == ''
        assert user['password'] == ''
        assert not user['registered']
        assert user['permissions'] == {}

        self.db.registerUser('test_user', 'user@test.dom', 'password')
        user = self.db.lookupUser('test_user')
        assert user['nickname'] == 'test_user'
        assert user['email'] == 'user@test.dom'
        assert user['password'] == 'password'
        assert user['registered']
        assert user['permissions'] == {}

    def test_deleteUser(self):
        self.db.createUser('test_user')
        user = self.db.lookupUser('test_user')
        assert user['nickname'] == 'test_user'
        assert user['email'] == ''
        assert user['password'] == ''
        assert not user['registered']
        assert user['permissions'] == {}

        self.db.deleteUser('test_user')
        user = self.db.lookupUser('test_user')
        assert user is None

    def test_setPermission(self):
        self.db.createUser('test_user', 'user@test.dom', 'pass', True)
        user = self.db.lookupUser('test_user')
        assert user['nickname'] == 'test_user'
        assert user['email'] == 'user@test.dom'
        assert user['password'] == 'pass'
        assert user['registered']
        assert user['permissions'] == {}
        self.db.setPermission('test_user', 'test_channel', '+s')
        user = self.db.lookupUser('test_user')
        assert user['permissions']['test_channel'] == ['+s']

    def test_createGroup(self):
        self.db.createGroup('test_channel', 'owner', 'public')
        channel = self.db.lookupGroup('test_channel')
        assert channel['name'] == 'test_channel'
        assert channel['owner'] == 'owner'
        assert channel['type'] == 'public'
        assert channel['topic'] != {}
        assert channel['messages'] == []

    def test_deleteGroup(self):
        self.db.createGroup('test_channel', 'owner', 'public')
        channel = self.db.lookupGroup('test_channel')
        assert channel['name'] == 'test_channel'
        assert channel['owner'] == 'owner'
        assert channel['type'] == 'public'
        assert channel['topic'] != {}
        assert channel['messages'] == []
        self.db.deleteGroup('test_channel')
        channel = self.db.lookupGroup('test_channel')
        assert channel is None

    def test_setGroupData(self):
        self.db.createGroup('test_channel', 'owner', 'public')
        channel = self.db.lookupGroup('test_channel')
        assert channel['name'] == 'test_channel'
        assert channel['owner'] == 'owner'
        assert channel['type'] == 'public'
        assert channel['topic'] != {}
        assert channel['messages'] == []
        self.db.setGroupTopic('test_channel', 'test', '1:23', 'author')
        channel = self.db.lookupGroup('test_channel')
        assert channel['topic']['topic'] == 'test'
        assert channel['topic']['topic_time'] == '1:23'
        assert channel['topic']['topic_author'] == 'author'

    def test_addMessage(self):
        self.db.createGroup('test_channel', 'owner', 'public')

        sender = "test_user"
        timestamp = "2014-10-15 10:14:51"
        text = "some text message"

        self.db.addMessage('test_channel',
                           sender,
                           timestamp,
                           text)

        sender2 = "other_user"
        timestamp2 = "2014-10-15 10:14:55"
        text2 = "response to text message"

        self.db.addMessage('test_channel',
                           sender2,
                           timestamp2,
                           text2)

        channel = self.db.lookupGroup('test_channel')
        assert channel['name'] == 'test_channel'
        assert channel['owner'] == 'owner'
        assert channel['type'] == 'public'
        assert channel['topic'] != {}
        assert channel['messages'][0]['sender'] == sender
        assert channel['messages'][0]['time'] == timestamp
        assert channel['messages'][0]['text'] == text

        assert channel['messages'][1]['sender'] == sender2
        assert channel['messages'][1]['time'] == timestamp2
        assert channel['messages'][1]['text'] == text2

    def test_checkIfValidEmail(self):
        email = "validemail@email.com"

        self.db.checkIfValidEmail(email)

    def test_checkIfValidNickname(self):
        nickname = "valid2013"

        self.db.checkIfValidNickname(nickname)

    def test_checkIfValidPassword(self):
        password = "goodPassword2"

        self.db.checkIfValidPassword(password)

    def test_privateMessage(self):
        sender = "sender"
        receiver = "receiver"
        timestamp = "2014-11-09 13:05:30"
        text = "private message"

        self.db.privateMessage(sender,
                               receiver,
                               timestamp,
                               text)

        channel = self.db.lookupGroup('receiver:sender')
        assert channel['name'] == 'receiver:sender'
        assert channel['type'] == 'private'

    def test_heartbeatsUserSession(self):
        result = self.db.heartbeatUserSession("test_user")
        assert result["inserted"] == 1

        result = self.db.heartbeatUserSession("test_user")
        assert result["replaced"] == 1

    def test_heartbeatUserInGroup(self):
        # Creates initial heartbeat
        result = self.db.heartbeatUserInGroup("test_user", "test_group")

        heartbeat_data = r.db(integration.DB).table("group_states").get(
            "test_group"
        ).run(self.conn)

        assert result["inserted"] == 1
        assert heartbeat_data["user_heartbeats"].get("test_user")

        # Updates user heartbeat
        result = self.db.heartbeatUserInGroup("test_user", "test_group")
        assert result["replaced"] == 1

        new_heartbeat_data = r.db(integration.DB).table("group_states").get(
            "test_group"
        ).run(self.conn)

        assert new_heartbeat_data["user_heartbeats"]["test_user"] != \
            heartbeat_data["user_heartbeats"]["test_user"]

    def test_removeUserFromGroup(self):
        self.db.heartbeatUserInGroup("test_user", "test_group")
        result = self.db.removeUserFromGroup("test_user", "test_group")

        assert result["replaced"] == 1

        heartbeat_data = r.db(integration.DB).table("group_states").get(
            "test_group"
        ).run(self.conn)

        assert False == heartbeat_data["user_heartbeats"].get("test_user",
                                                              False)

    def test_observesGroupStateChanges(self):
        self.db.heartbeatUserInGroup("john", "test_group")
        self.db.heartbeatUserInGroup("bob", "test_group")

        changefeed = self.db.observeGroupState("test_group")

        self.db.removeUserFromGroup("john", "test_group")

        change = next(changefeed)

        assert change["old_val"]["user_heartbeats"].get("john", None) is not None \
            and change["new_val"]["user_heartbeats"].get("john", None) is None
