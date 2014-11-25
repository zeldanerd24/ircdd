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

        hb = r.db(integration.DB).table("user_sessions").get(
            "john"
        ).run(self.conn)

        assert hb
        assert hb.get("last_heartbeat")
        assert hb.get("last_heartbeat") != ""

        self.ctx.db.heartbeatUserSession("john")
        hb2 = r.db(integration.DB).table("user_sessions").get(
            "john"
        ).run(self.conn)

        assert hb2
        assert hb2.get("last_heartbeat")
        assert hb2.get("last_heartbeat") != ""

        assert hb.get("last_heartbeat") != hb2.get("last_heartbeat")

    def test_userInGroupHeartbeats(self):
        group = ShardedGroup(self.ctx, "test_group")

        self.shardedUser.join(group)

        hb = r.db(integration.DB).table("group_states").get(
            "test_group"
        ).run(self.conn)

        assert hb
        assert hb["user_heartbeats"]["john"]
        assert hb["user_heartbeats"]["john"] != ""
