import rethinkdb as r
from rethinkdb.errors import RqlRuntimeError, RqlDriverError
from twisted.python import failure, log
from twisted.internet import defer


class IRCDDatabase:
    """
    Wrapper class for database actions, so that the IRC server
    does not have to know anything about how rethinkDB works
    in order to use it
    """

    USER_TABLE = 'users'
    CHANNEL_TABLE = 'channels'
    error = None

    def __init__(self, host, port, db_name='ircdd'):
        self.RDB_HOST = host
        self.RDB_PORT = port
        self.db_name = db_name

    def initializeDB(self):
        """
        Initialize the database if it is not already initialized
        """

        connection = r.connect(host=self.RDB_HOST, port=self.RDB_PORT)
        try:
            log.msg("Initializing the database")
            r.db_create(self.db_name).run(connection)
            r.db(self.db_name).table_create(self.USER_TABLE).run(connection)
            r.db(self.db_name).table_create(self.CHANNEL_TABLE).run(connection)
        except RqlRuntimeError, e:
            # this error occurs if the database is already initialized
            # not sure if any meaningful failures can also cause this exception
            log.msg(e)
            pass
        except Exception, e:
            # if a completely unexpected error comes up, cause a failure
            log.msg(e)
            self.error = defer.fail(failure.Failure(e))
        finally:
            connection.close()
            if self.error is not None:
                return self.error

    def dropDB(self):
        """
        Delete the database if it exists
        """

        connection = r.connect(host=self.RDB_HOST, port=self.RDB_PORT)
        try:
            r.db_drop(self.db_name).run(connection)
        except RqlRuntimeError, e:
            log.msg(e)
            pass

    def createUser(self, nickname, email, password, registered, permissions):
        """
        Add a user to the user table
        User table has the following fields:
        nickname (string), email (string), password (string),
        registered (boolean), permissions (dict of channel name: permissions
        contains channel name (string) and permissions (string))
        """

        try:
            rdb_conn = r.connect(host=self.RDB_HOST, port=self.RDB_PORT,
                                 db=self.db_name)
        except RqlDriverError:
            raise Exception("No database connection could be established.")

        # check to see if the user already exists and if so don't insert again
        cursor = r.table(self.USER_TABLE).filter(
            r.row['nickname'] == nickname).run(rdb_conn)
        num_duplicates = 0
        for document in cursor:
            num_duplicates = num_duplicates + 1
        if num_duplicates is 0:
            r.table(self.USER_TABLE).insert(
                {'nickname': nickname, 'email': email,
                 'password': password, 'registered': registered,
                 'permissions': permissions}
            ).run(rdb_conn)
        else:
            log.msg("Tried to add already existing user: %s" % nickname)

        try:
            rdb_conn.close()
        except AttributeError, e:
            log.msg(e)
            pass

    def lookupUser(self, nickname):
        """
        Finds the user with given nickname and returns the dict for it
        Returns None if the user is not found
        """

        try:
            rdb_conn = r.connect(host=self.RDB_HOST,
                                 port=self.RDB_PORT,
                                 db=self.db_name)
        except RqlDriverError:
            raise Exception("No database connection could be established.")

        cursor = r.table(self.USER_TABLE).filter(
            r.row['nickname'] == nickname).run(rdb_conn)
        rv = None
        for document in cursor:
            rv = document

        try:
            rdb_conn.close()
        except AttributeError, e:
            log.msg(e)
            pass
        return rv

    def registerUser(self, nickname, email, password):
        """
        Finds unregistered user with same nickname and registers them with
        the given email, password, and sets registered to True
        """

        try:
            rdb_conn = r.connect(host=self.RDB_HOST,
                                 port=self.RDB_PORT,
                                 db=self.db_name)
        except RqlDriverError:
            raise Exception("No database connection could be established.")

        result = r.table(self.USER_TABLE).filter(
            r.row['nickname'] == nickname).update({'email': email,
                                                   'password': password,
                                                   'registered': True}) \
                                          .run(rdb_conn)
        try:
            rdb_conn.close()
        except AttributeError, e:
            log.msg(e)
            pass
        return result

    def deleteUser(self, nickname):
        """
        Find and delete the user given by nickname
        """

        try:
            rdb_conn = r.connect(host=self.RDB_HOST, port=self.RDB_PORT,
                                 db=self.db_name)
        except RqlDriverError:
            raise Exception("No database connection could be established.")

        result = r.table(self.USER_TABLE).filter(
            r.row['nickname'] == nickname).delete().run(rdb_conn)
        try:
            rdb_conn.close()
        except AttributeError, e:
            log.msg(e)
            pass
        return result

    def setPermission(self, nickname, channel, permission):
        """
        Set permission for user for the given channel to the permissions string
        defined by permission
        """

        try:
            rdb_conn = r.connect(host=self.RDB_HOST,
                                 port=self.RDB_PORT, db=self.db_name)
        except RqlDriverError:
            raise Exception("No database connection could be established.")

        cursor = r.table(self.USER_TABLE).filter(
            r.row['nickname'] == nickname).run(rdb_conn)
        user = None
        result = None
        for document in cursor:
            user = document
        if user is not None:
            oldPermissions = user['permissions']
            if type(oldPermissions) is not dict:
                oldPermissions = {}
            oldPermissions[channel] = permission
            result = r.table(self.USER_TABLE).filter(
                r.row['nickname'] == nickname) \
                .update({'permissions': oldPermissions}).run(rdb_conn)
        try:
            rdb_conn.close()
        except AttributeError, e:
            log.msg(e)
            pass
        return result

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

        try:
            rdb_conn = r.connect(host=self.RDB_HOST,
                                 port=self.RDB_PORT, db=self.db_name)
        except RqlDriverError:
            raise Exception("No database connection could be established.")

        cursor = r.table(self.CHANNEL_TABLE).filter(
            r.row['name'] == name).run(rdb_conn)
        num_duplicates = 0
        for document in cursor:
            num_duplicates = num_duplicates + 1
        if num_duplicates is 0:
            r.table(self.CHANNEL_TABLE).insert({'name': name,
                                                'owner': owner,
                                                'type': channelType,
                                                'topic': '',
                                                'messages': ''}) \
                                       .run(rdb_conn)
        try:
            rdb_conn.close()
        except AttributeError, e:
            log.msg(e)
            pass

    def lookupGroup(self, name):
        """
        Return the IRC channel dict for channel with given name
        """

        try:
            rdb_conn = r.connect(host=self.RDB_HOST,
                                 port=self.RDB_PORT,
                                 db=self.db_name)
        except RqlDriverError:
            raise Exception("No database connection could be established.")

        cursor = r.table(self.CHANNEL_TABLE).filter(
            r.row['name'] == name).run(rdb_conn)
        rv = None
        for document in cursor:
            rv = document

        try:
            rdb_conn.close()
        except AttributeError, e:
            log.msg(e)
            pass
        return rv

    def listGroups(self):
        """
        Returns an array of all IRC channel names present in the database
        """

        try:
            rdb_conn = r.connect(host=self.RDB_HOST,
                                 port=self.RDB_PORT,
                                 db=self.db_name)
        except RqlDriverError:
            raise Exception("No database connection could be established.")

        cursor = r.table(self.CHANNEL_TABLE).run(rdb_conn)
        rv = []
        for document in cursor:
            rv.append(document['name'])

        try:
            rdb_conn.close()
        except AttributeError, e:
            log.msg(e)
            pass
        return rv

    def deleteGroup(self, name):
        """
        Delete the IRC channel with the given channel name
        """

        try:
            rdb_conn = r.connect(host=self.RDB_HOST, port=self.RDB_PORT,
                                 db=self.db_name)
        except RqlDriverError:
            raise Exception("No database connection could be established.")

        result = r.table(self.CHANNEL_TABLE).filter(
            r.row['name'] == name).delete().run(rdb_conn)
        try:
            rdb_conn.close()
        except AttributeError, e:
            log.msg(e)
            pass
        return result

    def setGroupData(self, channel_name, topic, topic_time, topic_author):
        """
        Set the IRC channel's topic
        """

        try:
            rdb_conn = r.connect(host=self.RDB_HOST,
                                 port=self.RDB_PORT, db=self.db_name)
        except RqlDriverError:
            raise Exception("No database connection could be established.")

        cursor = r.table(self.CHANNEL_TABLE).filter(
            r.row['name'] == channel_name).run(rdb_conn)
        channel = None
        result = None
        for document in cursor:
            channel = document
        if channel is not None:
            newTopic = {'topic': topic, 'topic_time': topic_time,
                        'topic_author': topic_author}
            result = r.table(self.CHANNEL_TABLE).filter(
                r.row['name'] == channel_name) \
                .update({'topic': newTopic}).run(rdb_conn)
        try:
            rdb_conn.close()
        except AttributeError, e:
            log.msg(e)
            pass
        return result

    def addMessage(self, nickname, channel_name, msg_time, msg_contents):
        """
        Add a message to IRC channel denoted by channel_name, written by nickname,
        and store the message time and contents
        """

        try:
            rdb_conn = r.connect(host=self.RDB_HOST,
                                 port=self.RDB_PORT, db=self.db_name)
        except RqlDriverError:
            raise Exception("No database connection could be established.")

        cursor = r.table(self.CHANNEL_TABLE).filter(
            r.row['name'] == channel_name).run(rdb_conn)
        channel = None
        result = None
        for document in cursor:
            channel = document
        if channel is not None:
            oldMessages = channel['messages']
            if type(oldMessages) is not list:
                oldMessages = []
            oldMessages.append({'nickname': nickname,
                                'time': msg_time,
                                'contents': msg_contents})
            result = r.table(self.CHANNEL_TABLE).filter(
                r.row['name'] == channel_name) \
                .update({'messages': oldMessages}).run(rdb_conn)
        try:
            rdb_conn.close()
        except AttributeError, e:
            log.msg(e)
            pass
        return result
