import nsq
import json


class RemoteReadWriter:
    """
    A high level producer/consumer for publishing/consuming from NSQ.
    Maintains a single long-lived `nsq.Writer`, a set of `nsq.Reader`s,
    and a set of callbacks. The mapping between `Reader`s and callbacks is 1:1.

    Expects a list of `NSQD` and `NSQLookupd` addresses to be passed along with
    a unique server identifier.

    :param nsqd_addresses: a list of strings in the form 'tcp_address:port'
    that correspond to ``NSQD`` instances that the writer should publish to.
    :type list:

    :param lookupd_addresses: a list of strings in the form 'http_address:port'
    that correspond to ``NSQLookupd`` instances that the readers should poll
    for producers.
    :type list:

    :param server_name: a string that uniquely idetifies this server instance.
    It will be used as channel name for both publishing and reading from `NSQ`.
    :type string:
    """

    def __init__(self, nsqd_addresses, lookupd_addresses, server_name):
        self._readers = {}
        self._writer = None
        self._nsqd_addresses = nsqd_addresses
        self._lookupd_addresses = lookupd_addresses
        self._server_name = server_name

    def subscribe(self, topic, callback):
        """
        Used to subscribe a callback to a topic. Typically used by
        :class:`ircdd.server.IRCDDUser` and :class:`ircdd.server.IRCDDGroup`.
        It will spin up a new :class:`nsq.Reader` for the given topic if one
        does not exist already and register the given callback with it.
        Only one callback per topic exists.

        :param topic: a string which identifies the topic on which to listen.
        :type string:

        :param callback: the callback which will be called when a message is
        read. The callback must take a single argument (`message`),
        call :meth:`nsq.Message.finish()`/:meth:`nsq.Message.requeue()` and
        return `True`/`False` when it is done with the message. The callback
        can expect `message` to be :class:`nsq.Message`, with an additional
        attribute `parsed_body` which contains the `json` parsed body of the
        message (still available in raw from through the `body` attribute).
        :type callable:
        """

        if self._readers.get(topic, None) is None:
            reader = nsq.Reader(message_handler=self.filter_callback(callback),
                                lookupd_http_addresses=self._lookupd_addresses,
                                topic=topic,
                                channel=self._server_name,
                                lookupd_poll_interval=15)
            self._readers[topic] = reader

    def filter_callback(self, callback):
        """
        Decorator function which wraps the given callback in
        a filter that discards messages which originated from this server
        instance server.

        :param callback: the callback which will be wrapped
        :type callable:
        """

        def filtered_callback(message):
            parsed_body = json.loads(message.body)

            if parsed_body['origin'] == self._server_name:
                message.finish()
                return True
            else:
                message.parsed_body = parsed_body
                return callback(message)

        return filtered_callback

    def unsubscribe(self, topic):
        """
        Unsubscribes a callback from the given topic. Typically used by
        :class:`ircdd.server.IRCDDUser` and :class:`ircdd.server.IRCDDGroup`.
        It will shut down the reader.

        :param topic: the topic for which to stop listening.
        :type string:
        """
        self._readers[topic].close()
        del self._readers[topic]

    def publish(self, topic, msg_body, callback=None):
        """
        Publishes a message to the given queue and calls
        the optional callback once completed. Creates the
        writer if it does not exist. The message is wrapped in
        a container dictionary that wears the origin tag,
        json formatted, and then given to the writer.

        :param topic: the name of the topic to publish to
        :type string:

        :param msg: the message to publish
        :type string:

        :param callback: an optional callback which will be
        called once :method:`nsq.Writer.pub()` completes.
        :type callable:
        """

        if self._writer is None:
            self._writer = nsq.Writer(self._nsqd_addresses)

        msg = dict(text=msg_body, origin=self._server_name)
        self._writer.pub(topic, json.dumps(msg), callback=callback)