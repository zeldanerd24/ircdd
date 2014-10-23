import mock
from ircdd.remote import RemoteReadWriter
from nose.tools import assert_raises


class TestRemoteReadWriter:

    @mock.patch("nsq.Writer")
    @mock.patch("nsq.Reader")
    @mock.patch("tornado.ioloop.IOLoop")
    def testSubscribes(self, mock_writer, mock_reader, mock_ioloop):
        server_name = "testserver"
        nsqd_addr = ["testserver:4533"]
        lookupd_addr = ["testserver:5566"]

        rw = RemoteReadWriter(nsqd_addr, lookupd_addr, server_name)

        topic = "testopic"
        callback = "callback"

        rw.subscribe(topic, callback)

        assert rw._readers.get(topic, False)

    @mock.patch("nsq.Writer")
    @mock.patch("nsq.Reader")
    @mock.patch("tornado.ioloop.IOLoop")
    def testUnsubscribes(self, mock_writer, mock_reader, mock_ioloop):
        server_name = "testserver"
        nsqd_addr = ["testserver:4533"]
        lookupd_addr = ["testserver:5566"]

        rw = RemoteReadWriter(nsqd_addr, lookupd_addr, server_name)

        topic = "testopic"
        callback = "callback"

        rw.subscribe(topic, callback)

        rw.unsubscribe(topic)

        assert rw._readers.get(topic, None) is None

    @mock.patch("nsq.Writer")
    @mock.patch("nsq.Reader")
    @mock.patch("tornado.ioloop.IOLoop")
    def testUnsubscribeFails(self, mock_writer, mock_reader, mock_ioloop):
        server_name = "testserver"
        nsqd_addr = ["testserver:4533"]
        lookupd_addr = ["testserver:5566"]

        rw = RemoteReadWriter(nsqd_addr, lookupd_addr, server_name)

        topic = "testopic"

        assert_raises(KeyError, rw.unsubscribe, topic)

    @mock.patch("nsq.Writer")
    @mock.patch("nsq.Reader")
    @mock.patch("nsq.Message")
    @mock.patch("tornado.ioloop.IOLoop")
    def testFilteredMethodFilters(self, mock_w, mock_r, mock_m, mock_io):
        server_name = "testserver"
        nsqd_addr = ["testserver:4533"]
        lookupd_addr = ["testserver:5566"]

        rw = RemoteReadWriter(nsqd_addr, lookupd_addr, server_name)

        def testCallback(message):
            return message.parsed_body["message"]

        filteredCb = rw.filter_callback(testCallback)

        mock_m.body = """{\"origin\": \"testserver\",
                        \"message\": \"am I getting filtered?"
                      }"""

        assert filteredCb(mock_m) != mock_m.parsed_body["message"]

    @mock.patch("nsq.Writer")
    @mock.patch("nsq.Reader")
    @mock.patch("nsq.Message")
    @mock.patch("tornado.ioloop.IOLoop")
    def testFilteredMethodPassThrough(self, mock_w, mock_r, mock_m, mock_io):
        server_name = "testserver"
        nsqd_addr = ["testserver:4533"]
        lookupd_addr = ["testserver:5566"]

        rw = RemoteReadWriter(nsqd_addr, lookupd_addr, server_name)

        def testCallback(message):
            return message.parsed_body["message"]

        filteredCb = rw.filter_callback(testCallback)

        mock_m.body = """{\"origin\": \"otherserver\",
                        \"message\": \"am I getting filtered?"
                      }"""

        assert filteredCb(mock_m) == mock_m.parsed_body["message"]
