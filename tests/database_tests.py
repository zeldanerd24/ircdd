from ircdd import database
import unittest


class TestIRCDDatabase(unittest.TestCase):

    db = database.IRCDDatabase('localhost', 28015, 'testdb')

    def setUp(self):
        self.db = database.IRCDDatabase('localhost', 28015, 'testdb')
        self.db.dropDB()
        self.db.initializeDB()

    def test_createUser(self):
        self.db.createUser('test_user', 'a@b.c', 'pass', True, '')
        user = self.db.lookupUser('test_user')
        assert user['nickname'] == "test_user"
        assert user['email'] == 'a@b.c'
        assert user['password'] == 'pass'
        assert user['registered']
        assert user['permissions'] == ''

    def test_registerUser(self):
        self.db.createUser('test_user', '', '', False, '')
        user = self.db.lookupUser('test_user')
        assert user['nickname'] == 'test_user'
        assert user['email'] == ''
        assert user['password'] == ''
        assert not user['registered']
        assert user['permissions'] == ''
        self.db.registerUser('test_user', 'a@b.c', 'password')
        user = self.db.lookupUser('test_user')
        assert user['nickname'] == 'test_user'
        assert user['email'] == 'a@b.c'
        assert user['password'] == 'password'
        assert user['registered']
        assert user['permissions'] == ''

    def test_deleteUser(self):
        self.db.createUser('test_user', '', '', False, '')
        user = self.db.lookupUser('test_user')
        assert user['nickname'] == 'test_user'
        assert user['email'] == ''
        assert user['password'] == ''
        assert not user['registered']
        assert user['permissions'] == ''
        self.db.deleteUser('test_user')
        user = self.db.lookupUser('test_user')
        assert user is None

    def test_setPermission(self):
        self.db.createUser('test_user', 'a@b.c', 'pass', True, '')
        user = self.db.lookupUser('test_user')
        assert user['nickname'] == 'test_user'
        assert user['email'] == 'a@b.c'
        assert user['password'] == 'pass'
        assert user['registered']
        assert user['permissions'] == ''
        self.db.setPermission('test_user', 'test_channel', '+s')
        user = self.db.lookupUser('test_user')
        assert user['permissions']['test_channel'] == '+s'

    def test_createGroup(self):
        self.db.createGroup('test_channel', 'owner', 'public')
        channel = self.db.lookupGroup('test_channel')
        assert channel['name'] == 'test_channel'
        assert channel['owner'] == 'owner'
        assert channel['type'] == 'public'
        assert channel['topic'] == ''
        assert channel['messages'] == ''

    def test_deleteGroup(self):
        self.db.createGroup('test_channel', 'owner', 'public')
        channel = self.db.lookupGroup('test_channel')
        assert channel['name'] == 'test_channel'
        assert channel['owner'] == 'owner'
        assert channel['type'] == 'public'
        assert channel['topic'] == ''
        assert channel['messages'] == ''
        self.db.deleteGroup('test_channel')
        channel = self.db.lookupGroup('test_channel')
        assert channel is None

    def test_setGroupData(self):
        self.db.createGroup('test_channel', 'owner', 'public')
        channel = self.db.lookupGroup('test_channel')
        assert channel['name'] == 'test_channel'
        assert channel['owner'] == 'owner'
        assert channel['type'] == 'public'
        assert channel['topic'] == ''
        assert channel['messages'] == ''
        self.db.setGroupData('test_channel', 'test', '1:23', 'author')
        channel = self.db.lookupGroup('test_channel')
        assert channel['topic']['topic'] == 'test'
        assert channel['topic']['topic_time'] == '1:23'
        assert channel['topic']['topic_author'] == 'author'

    def test_addMessage(self):
        self.db.createGroup('test_channel', 'owner', 'public')
        self.db.addMessage('test_user', 'test_channel', '1:23',
                           'this is a msg')
        self.db.addMessage('test_user2', 'test_channel', '1:24',
                           'this is another msg')
        channel = self.db.lookupGroup('test_channel')
        assert channel['name'] == 'test_channel'
        assert channel['owner'] == 'owner'
        assert channel['type'] == 'public'
        assert channel['topic'] == ''
        assert channel['messages'][0]['nickname'] == 'test_user'
        assert channel['messages'][0]['time'] == '1:23'
        assert channel['messages'][0]['contents'] == 'this is a msg'
        assert channel['messages'][1]['nickname'] == 'test_user2'
        assert channel['messages'][1]['time'] == '1:24'
        assert channel['messages'][1]['contents'] == 'this is another msg'
