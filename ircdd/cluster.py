import nsq

class ChannelCaster:
    _callbacks = {}
    _writer = None
    _readers = {}

    def __init__(self, ctx):
        self.ctx = ctx
        self._writer = nsq.Writer(ctx['nsqd_tcp_addresses'])

    def subscribe(self, topic, protocol_name, callback):
        if self._callbacks.get(topic, None) is None:
            self._callbacks[topic] = {}

        self._callbacks[topic][protocol_name] = callback

        if self._readers.get(topic, None) is None:
            self._readers[topic] = nsq.Reader(message_handler=self._reader_callback(topic),
                    lookupd_http_addresses=self.ctx['nsqlookupd_http_addresses'],
                    topic=topic,
                    channel=protocol_name,
                    lookupd_poll_interval=15)
            nsq.run()

    def unsibscribe(self, topic, protocol_name):
        self._callbacks[topic][protocol_name] = None

    def unsubscribe_all(self, protocol_name):
        for topic, callbacks in self._callbacks:
            if callbacks.get(protocol_name, None):
                callbacks[protocol_name] = None

    def _reader_callback(self, topic):
        def topic_callback(message):
            for p, c in self._callbacks[topic]:
                c(message)
            return True
        return topic_callback
