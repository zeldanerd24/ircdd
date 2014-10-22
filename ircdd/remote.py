import nsq


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

        self._writer = nsq.Writer(nsqd_addresses)
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
        read. The callback must take a single argument (`message`) and either
        call :meth:`nsq.Message.finish()`/:meth:`nsq.Message.requeue()` or
        return `True`/`False` when it is done with the message.
        :type callable:
        """

        if self._readers.get(topic, None) is None:
            reader = nsq.Reader(message_handler=callback,
                                lookupd_http_addresses=self._lookupd_addresses,
                                topic=topic,
                                channel=self._server_name,
                                lookupd_poll_interval=15)
            self._readers[topic] = reader
            nsq.run()

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
