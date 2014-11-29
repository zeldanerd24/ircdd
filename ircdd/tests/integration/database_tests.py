import rethinkdb as r
from ircdd import database

from ircdd.tests import integration


class TestIRCDDatabase():
    def setUp(self):
        self.conn = r.connect(db=integration.DB,
                              host=integration.HOST,
                              port=integration.PORT)

        self.db = database.IRCDDatabase(integration.DB,
                                        integration.HOST,
                                        integration.PORT)

    def tearDown(self):
        integration.cleanTables()

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
        self.db.createGroup('test_channel', 'public')

        group = self.db.lookupGroup('test_channel')

        assert group['name'] == 'test_channel'
        assert group['type'] == 'public'
        assert group['meta'] != {}
        assert group['messages'] == []
        assert group["users"] == {}

    def test_deleteGroup(self):
        self.db.createGroup('test_channel', 'public')
        channel = self.db.lookupGroup('test_channel')
        assert channel['name'] == 'test_channel'
        assert channel['type'] == 'public'
        assert channel['meta'] != {}
        assert channel['messages'] == []

        self.db.deleteGroup('test_channel')

        channel = self.db.lookupGroup('test_channel')
        assert channel is None

        state = self.db.getGroupState("test_channel")
        assert state is None

    def test_setGroupData(self):
        self.db.createGroup('test_channel', 'public')
        channel = self.db.lookupGroup('test_channel')
        assert channel['name'] == 'test_channel'
        assert channel['type'] == 'public'
        assert channel['meta'] != {}
        assert channel['messages'] == []

        self.db.setGroupTopic('test_channel', 'test', 'john_doe')
        channel = self.db.lookupGroup('test_channel')

        assert channel['meta']['topic'] == 'test'
        assert channel['meta']['topic_time']
        assert channel['meta']['topic_author'] == 'john_doe'

    def test_checkIfValidEmail(self):
        email = "validemail@email.com"

        self.db.checkIfValidEmail(email)

    def test_checkIfValidNickname(self):
        nickname = "valid2013"

        self.db.checkIfValidNickname(nickname)

    def test_checkIfValidPassword(self):
        password = "goodPassword2"

        self.db.checkIfValidPassword(password)

    def test_heartbeatsUserSession(self):
        result = self.db.heartbeatUserSession("test_user")
        assert result["inserted"] == 1

        result = self.db.heartbeatUserSession("test_user")
        assert result["replaced"] == 1

    def test_heartbeatUserInGroup(self):
        # Creates initial heartbeat
        result = self.db.heartbeatUserInGroup("test_user", "test_group")
        group_state = self.db.getGroupState("test_group")

        assert result["inserted"] == 1
        assert group_state["users"].get("test_user")

        # Updates user heartbeat
        result = self.db.heartbeatUserInGroup("test_user", "test_group")
        assert result["replaced"] == 1

        new_group_state = self.db.getGroupState("test_group")
        assert new_group_state["users"]["test_user"] != \
            group_state["users"]["test_user"]

    def test_removeUserFromGroup(self):
        self.db.heartbeatUserInGroup("test_user", "test_group")
        result = self.db.removeUserFromGroup("test_user", "test_group")

        assert result["replaced"] == 1

        group_state = self.db.getGroupState("test_group")
        assert False == group_state["users"].get("test_user",
                                                 False)

    def test_observesGroupStateChanges(self):
        self.db.heartbeatUserInGroup("john", "test_group")
        self.db.heartbeatUserInGroup("bob", "test_group")

        changefeed = self.db.observeGroupState("test_group")

        self.db.removeUserFromGroup("john", "test_group")

        change = next(changefeed)

        assert change["old_val"]["users"].get("john", None) is not None \
            and change["new_val"]["users"].get("john", None) is None
