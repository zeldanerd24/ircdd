import nsq


class RemoteReadWriter:
    _observers = {}
    _writer = None
    _readers = {}
    _lookupd_addresses = None
    _server_name = None

    def __init__(self, nsqd_addresses, lookupd_addresses, server_name):
        self._writer = nsq.Writer(nsqd_addresses)
        self._lookupd_addresses = lookupd_addresses
        self._server_name = server_name

    def subscribe(self, topic, callback):
        self._callbacks[topic] = callback

        if self._readers.get(topic, None) is None:
            reader = nsq.Reader(message_handler=self.filtered_callback(topic),
                                lookupd_http_addresses=self.lookupd_addresses,
                                topic=topic,
                                channel=self.server_name,
                                lookupd_poll_interval=15)
            self._readers[topic] = reader
            nsq.run()

    def unsibscribe(self, topic):
        self._callbacks[topic] = None
        self._readers[topic].close()

    def filter_callback(self, topic):
        def filtered_callback(message):
            # discard messages which originate here
            self._observers[topic](message)
            return True
    return filtered_callback
