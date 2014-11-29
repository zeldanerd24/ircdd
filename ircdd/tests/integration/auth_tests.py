import rethinkdb as r

from twisted.test import proto_helpers
from twisted.words.protocols import irc

from ircdd.server import IRCDDFactory
from ircdd.remote import _topics
from ircdd.remote import _delete_topic
from ircdd.context import makeContext
from ircdd.tests import integration


class TestIRCDDAuth:
    def setUp(self):
        self.conn = r.connect(db=integration.DB,
                              host=integration.HOST,
                              port=integration.PORT)

        self.nodes = 3

        self.configs = []
        self.ctx = []
        self.factories = []
        self.protocols = []
        self.transports = []

        for node in xrange(0, self.nodes):
            config = dict(nsqd_tcp_address=["127.0.0.1:4150"],
                          lookupd_http_address=["127.0.0.1:4161"],
                          hostname="testserver%s" % node,
                          group_on_request=True,
                          user_on_request=True,
                          db=integration.DB,
                          rdb_host=integration.HOST,
                          rdb_port=integration.PORT
                          )
            self.configs.append(config)

            ctx = makeContext(config)
            self.ctx.append(ctx)

            factory = IRCDDFactory(ctx)
            self.factories.append(factory)

            protocol = factory.buildProtocol(("127.0.0.1", 0))
            self.protocols.append(protocol)

            transport = proto_helpers.StringTransport()
            self.transports.append(transport)

            protocol.makeConnection(transport)

    def tearDown(self):
        for transport in self.transports:
            transport.loseConnection()
        self.transports = None

        for protocol in self.protocols:
            protocol.connectionLost(None)
        self.protocols = None

        self.factories = None
        self.configs = None

        for ctx in self.ctx:
            ctx.db.conn.close()
        self.ctx = None

        for topic in _topics(["127.0.0.1:4161"]):
            _delete_topic(topic, ["127.0.0.1:4161"])

        integration.cleanTables()

        self.conn.close()

    def getResponse(self, protocol):
        response = protocol.transport.value().splitlines()
        protocol.transport.clear()
        return map(irc.parsemsg, response)

    def test_anon_login(self):
        node = 0

        protocol = self.protocols[node]
        factory = self.factories[node]
        hostname = factory.ctx.hostname

        protocol.irc_NICK("", ["anonuser"])

        version = ("Your host is %s, running version %s" %
                   (hostname, factory._serverInfo["serviceVersion"]))

        creation = ("This server was created on %s" %
                    (factory._serverInfo["creationDate"]))
        expected = [(hostname, "375",
                    ["anonuser", "- %s Message of the Day - " % hostname]),
                    (hostname, "376",
                    ["anonuser", "End of /MOTD command."]),
                    (hostname, "001",
                    ["anonuser", "connected to Twisted IRC"]),
                    (hostname, "002", ["anonuser", version]),
                    (hostname, "003", ["anonuser", creation]),
                    (hostname, "004",
                    ["anonuser", hostname,
                     factory._serverInfo["serviceVersion"], "w", "n"])]

        response = self.getResponse(protocol)
        assert response == expected

    def test_registered_login(self):
        """
        Connecting to the server, sending /pass <pw>,
        then /nick <name> logs the registered user in.
        """
        node = 0

        ctx = self.ctx[node]
        ctx.db.createUser("john", password="pw", registered=True)

        protocol = self.protocols[node]
        protocol.irc_PASS("", ["pw"])
        protocol.irc_NICK("", ["john"])

        factory = self.factories[node]
        hostname = factory.ctx.hostname

        version = ("Your host is %s, running version %s" %
                   (hostname, factory._serverInfo["serviceVersion"]))

        creation = ("This server was created on %s" %
                    (factory._serverInfo["creationDate"]))
        expected = [(hostname, "375",
                    ["john", "- %s Message of the Day - " % hostname]),
                    (hostname, "376",
                    ["john", "End of /MOTD command."]),
                    (hostname, "001",
                    ["john", "connected to Twisted IRC"]),
                    (hostname, "002", ["john", version]),
                    (hostname, "003", ["john", creation]),
                    (hostname, "004",
                    ["john", hostname,
                     factory._serverInfo["serviceVersion"], "w", "n"])]

        response = self.getResponse(protocol)
        assert response == expected

    def test_anon_login_create_fail(self):
        node = 0

        ctx = self.ctx[node]
        ctx.realm.createUserOnRequest = False

        protocol = self.protocols[node]
        protocol.irc_NICK("", ["anonuser"])

        factory = self.factories[node]
        hostname = factory.ctx.hostname

        version = ("Your host is %s, running version %s" %
                   (hostname, factory._serverInfo["serviceVersion"]))

        creation = ("This server was created on %s" %
                    (factory._serverInfo["creationDate"]))
        expected = [(hostname, "375",
                    ["anonuser", "- %s Message of the Day - " % hostname]),
                    (hostname, "376",
                    ["anonuser", "End of /MOTD command."]),
                    (hostname, "001",
                    ["anonuser", "connected to Twisted IRC"]),
                    (hostname, "002", ["anonuser", version]),
                    (hostname, "003", ["anonuser", creation]),
                    (hostname, "004",
                    ["anonuser", hostname,
                     factory._serverInfo["serviceVersion"], "w", "n"])]

        response = self.getResponse(protocol)
        # Improve this to expect a specific error output
        assert response != expected

    def test_anon_login_nick_taken_fail(self):
        success_node = 0

        protocol = self.protocols[success_node]
        protocol.irc_NICK("", ["anonuser"])

        factory = self.factories[success_node]
        hostname = factory.ctx.hostname

        version = ("Your host is %s, running version %s" %
                   (hostname, factory._serverInfo["serviceVersion"]))

        creation = ("This server was created on %s" %
                    (factory._serverInfo["creationDate"]))
        expected = [(hostname, "375",
                    ["anonuser", "- %s Message of the Day - " % hostname]),
                    (hostname, "376",
                    ["anonuser", "End of /MOTD command."]),
                    (hostname, "001",
                    ["anonuser", "connected to Twisted IRC"]),
                    (hostname, "002", ["anonuser", version]),
                    (hostname, "003", ["anonuser", creation]),
                    (hostname, "004",
                    ["anonuser", hostname,
                     factory._serverInfo["serviceVersion"], "w", "n"])]

        response = self.getResponse(protocol)
        assert response == expected

        fail_node = 1
        fail_protocol = self.protocols[fail_node]
        fail_protocol.irc_NICK("", ["anonuser"])

        fail_factory = self.factories[fail_node]
        fail_hostname = fail_factory.ctx.hostname

        expected = [(fail_hostname, '375',
                     ['anonuser', '- %s Message of the Day - ' %
                         fail_hostname]),
                    (fail_hostname, '376',
                     ['anonuser', 'End of /MOTD command.']),
                    ('NickServ!NickServ@services', 'PRIVMSG',
                     ['anonuser', 'Already logged in.  No pod people allowed!']
                     )]
        response_fail = self.getResponse(fail_protocol)

        assert response_fail == expected

    def test_registered_login_pw_fail(self):
        node = 0

        ctx = self.ctx[node]
        ctx.db.createUser("john", password="pw", registered=True)

        protocol = self.protocols[node]
        protocol.irc_PASS("", ["bad_password"])
        protocol.irc_NICK("", ["john"])

        factory = self.factories[node]
        hostname = factory.ctx.hostname

        expected = [(hostname, '375',
                    ['john', '- %s Message of the Day - ' % hostname]),
                    (hostname, '376', ['john', 'End of /MOTD command.']),
                    ('NickServ!NickServ@services', 'PRIVMSG',
                    ['john', 'Login failed.  Goodbye.'])]

        response = self.getResponse(protocol)
        assert response == expected
