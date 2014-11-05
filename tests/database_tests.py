import rethinkdb as r
from ircdd import database

DB = "test_ircdd"
HOST = "127.0.0.1"
PORT = 28015

USERS_TABLE = "users"
GROUPS_TABLE = "groups"


def setUp():
    conn = r.connect(db=DB, host=HOST, port=PORT)
    r.db_create(DB).run(conn)
    conn.close()


def tearDown():
    conn = r.connect(db=DB, host=HOST, port=PORT)
    r.db_drop(DB).run(conn)
    conn.close()


class TestIRCDDatabase():
    def setUp(self):
        conn = r.connect(db=DB, host=HOST, port=PORT)
        r.db(DB).table_create("users").run(conn)
        r.db(DB).table_create("groups").run(conn)
        conn.close()

        self.db = database.IRCDDatabase(HOST, PORT, DB)

    def tearDown(self):
        conn = r.connect(db=DB, host=HOST, port=PORT)
        r.db(DB).table_drop("users").run(conn)
        r.db(DB).table_drop("groups").run(conn)
        conn.close()

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
        assert channel['topic'] == {}
        assert channel['messages'] == []

    def test_deleteGroup(self):
        self.db.createGroup('test_channel', 'owner', 'public')
        channel = self.db.lookupGroup('test_channel')
        assert channel['name'] == 'test_channel'
        assert channel['owner'] == 'owner'
        assert channel['type'] == 'public'
        assert channel['topic'] == {}
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
        assert channel['topic'] == {}
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
        assert channel['topic'] == {}
        assert channel['messages'][0]['sender'] == sender
        assert channel['messages'][0]['time'] == timestamp
        assert channel['messages'][0]['text'] == text

        assert channel['messages'][1]['sender'] == sender2
        assert channel['messages'][1]['time'] == timestamp2
        assert channel['messages'][1]['text'] == text2
