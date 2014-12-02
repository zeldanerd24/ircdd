import rethinkdb as r

from twisted.test import proto_helpers
from twisted.words.protocols import irc

from ircdd.server import IRCDDFactory
from ircdd.remote import _topics
from ircdd.remote import _delete_topic
from ircdd.context import makeContext
from ircdd.tests import integration


class TestMessaging():
    def setUp(self):
        self.conn = r.connect(db=integration.DB,
                              host=integration.HOST,
                              port=integration.PORT)

        self.protocols = []
        self.transports = []

        self.config = dict(nsqd_tcp_address=["127.0.0.1:4150"],
                           lookupd_http_address=["127.0.0.1:4161"],
                           hostname="testserver",
                           group_on_request=True,
                           user_on_request=True,
                           db=integration.DB,
                           rdb_host=integration.HOST,
                           rdb_port=integration.PORT
                           )

        self.ctx = makeContext(self.config)

        self.factory = IRCDDFactory(self.ctx)

        self.clients = 3
        for client in xrange(0, self.clients):

            protocol = self.factory.buildProtocol(("127.0.0.%s" % client, 0))
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

        self.factory = None
        self.config = None

        self.ctx.db.conn.close()
        self.ctx = None

        for topic in _topics(["127.0.0.1:4161"]):
            _delete_topic(topic, ["127.0.0.1:4161"])

        integration.cleanTables()

        self.conn.close()

    def getResponse(self, protocol):
        response = protocol.transport.value().splitlines()
        protocol.transport.clear()
        return map(irc.parsemsg, response)

    def test_join_msg(self):
        john_protocol = self.protocols[0]
        hostname = self.factory.ctx.hostname

        john_protocol.irc_NICK("", ["john"])
        john_protocol.irc_JOIN("", ["testchan"])

        version = ("Your host is %s, running version %s" %
                   (hostname, self.factory._serverInfo["serviceVersion"]))

        creation = ("This server was created on %s" %
                    (self.factory._serverInfo["creationDate"]))

        expected = [(hostname, '375',
                    ['john', '- %s Message of the Day - ' % hostname]),
                    (hostname, '376',
                    ['john', 'End of /MOTD command.']),
                    (hostname, '001',
                    ['john', 'connected to Twisted IRC']),
                    (hostname, '002', ['john', version]),
                    (hostname, '003', ['john', creation]),
                    (hostname, '004',
                    ['john', hostname,
                     self.factory._serverInfo["serviceVersion"], 'w', 'n']),
                    ('john!john@%s' % hostname, 'JOIN', ['#testchan']),
                    (hostname, '366',
                    ['john', '#testchan', 'End of /NAMES list'])]

        assert expected == self.getResponse(john_protocol)

        jane_protocol = self.protocols[1]

        jane_protocol.irc_NICK("", ["jane"])
        jane_protocol.irc_JOIN("", ["testchan"])

        expected_notification = [('jane!jane@%s' % hostname,
                                  'JOIN', ['#testchan'])]
        assert expected_notification == self.getResponse(john_protocol)

        expected_join = [(hostname, '375',
                         ['jane', '- %s Message of the Day - ' % hostname]),
                         (hostname, '376',
                         ['jane', 'End of /MOTD command.']),
                         (hostname, '001',
                         ['jane', 'connected to Twisted IRC']),
                         (hostname, '002', ['jane', version]),
                         (hostname, '003', ['jane', creation]),
                         (hostname, '004',
                         ['jane', hostname,
                          self.factory._serverInfo["serviceVersion"],
                          'w', 'n']),
                         ('jane!jane@%s' % hostname, 'JOIN', ['#testchan']),
                         (hostname, '366',
                         ['jane', '#testchan', 'End of /NAMES list'])]

        assert expected_join == self.getResponse(jane_protocol)

    def test_part_msg(self):
        john_protocol = self.protocols[0]
        jane_protocol = self.protocols[1]

        john_protocol.irc_NICK("", ["john"])
        john_protocol.irc_JOIN("", ["testchan"])

        jane_protocol.irc_NICK("", ["jane"])
        jane_protocol.irc_JOIN("", ["testchan"])

        # Discard responses up until this point
        self.getResponse(john_protocol)
        self.getResponse(jane_protocol)

        john_protocol.irc_PART("", ["testchan"])

        expected = [('john!john@testserver', 'PART', ['#testchan', 'leaving'])]

        assert expected == self.getResponse(jane_protocol)
        assert expected == self.getResponse(john_protocol)

    def test_chan_message(self):
        pass

    def test_set_topic_msg(self):
        pass
