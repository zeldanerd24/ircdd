import rethinkdb as r

from twisted.test import proto_helpers

from ircdd.user import ShardedUser
from ircdd.group import ShardedGroup
from ircdd.server import IRCDDFactory
from ircdd.remote import _channels, _topics
from ircdd.remote import _delete_channel, _delete_topic
from ircdd.context import makeContext
from ircdd.tests import integration


class TestShardedUser:
    def setUp(self):
        self.conn = r.connect(db=integration.DB,
                              host=integration.HOST,
                              port=integration.PORT)

        integration.createTables()

        config = dict(nsqd_tcp_address=["127.0.0.1:4150"],
                      lookupd_http_address=["127.0.0.1:4161"],
                      hostname="testserver",
                      group_on_request=True,
                      user_on_request=True,
                      db=integration.DB,
                      rdb_host=integration.HOST,
                      rdb_port=integration.PORT
                      )
        self.ctx = makeContext(config)

        self.factory = IRCDDFactory(self.ctx)
        self.protocol = self.factory.buildProtocol(("127.0.0.1", 0))
        self.transport = proto_helpers.StringTransport()
        self.protocol.makeConnection(self.transport)

        self.shardedUser = ShardedUser(self.ctx, "john")
        self.shardedUser.mind = self.protocol
        self.shardedUser.mind.name = "john"

    def tearDown(self):
        self.shardedUser = None
        self.transport.loseConnection()
        self.protocol.connectionLost(None)

        integration.dropTables()

        self.conn.close()

        for topic in _topics(self.ctx["lookupd_http_address"]):
            for chan in _channels(topic, self.ctx["lookupd_http_address"]):
                _delete_channel(topic, chan, self.ctx["lookupd_http_address"])
            _delete_topic(topic, self.ctx["lookupd_http_address"])

        self.ctx["db"].conn.close()
        self.ctx = None

    def test_userHeartbeats(self):
        self.shardedUser.loggedIn(self.ctx.realm, None)

        session = self.ctx.db.lookupUserSession("john")

        assert session
        assert session.get("last_heartbeat")
        assert session.get("last_heartbeat") != ""

        self.ctx.db.heartbeatUserSession("john")
        updated_session = self.ctx.db.lookupUserSession("john")

        assert updated_session
        assert updated_session.get("last_heartbeat")
        assert updated_session.get("last_heartbeat") != ""

        assert session.get("last_heartbeat") != \
            updated_session.get("last_heartbeat")

    def test_userInGroupHeartbeats(self):
        group = ShardedGroup(self.ctx, "test_group")

        self.shardedUser.join(group)

        group_state = self.ctx.db.getGroupState("test_group")

        assert group_state
        assert group_state["users"]["john"]
        assert group_state["users"]["john"] != ""
