import nsq
import json
import requests
from requests.exceptions import ConnectionError, Timeout
from twisted.python import log


def _create_topic(topic, lookupd_http_addresses):
    """
    Utility function which creates the requested topic
    on each of the given lookupd http addresses.
    :param topic: The name of the topic to create.
    :type string:
    :param lookupd_http_adddresses: A list of address
    strings that point to `NSQLookupd` instances.
    :type list:
    """
    for addr in lookupd_http_addresses:
        # create_topic URI is deprecated but the
        # does not work so use this instead
        endpoint = "http://%s/create_topic" % addr
        params = {"topic": topic}

        try:
            response = requests.get(endpoint, params=params, timeout=5)
        except (ConnectionError, Timeout) as e:
            log.err("Error making request to NSQLookupd: %s" % str(e))
        else:
            if response.status_code != requests.codes.ok:
                log.err("Failed to create topic %s on %s: %s" %
                        (topic, endpoint, str(response)))


def _topics(lookupd_http_addresses):
    """
    Utility function which lists the known topics
    on each of the given lookupd http addresses.
    :param lookupd_http_adddresses: A list of address
    strings that point to `NSQLookupd` instances.
    :type list:
    """
    for addr in lookupd_http_addresses:
        endpoint = "http://%s/topics" % addr

        try:
            response = requests.get(endpoint, timeout=5)
        except (ConnectionError, Timeout) as e:
            log.err("Error making request to NSQLookupd: %s" % str(e))
        else:
            if response.status_code != requests.codes.ok:
                log.err("Failed to list topics on %s: %s" %
                        (endpoint, str(response)))
            else:
                return response.json()["data"]["topics"]


def _delete_topic(topic, lookupd_http_addresses):
    """
    Utility function which deletes the requested topic
    on each of the given lookupd http addresses.
    :param topic: The name of the topic to empty.
    :type string:
    :param lookupd_http_adddresses: A list of address
    strings that point to `NSQLookupd` instances.
    :type list:
    """
    for addr in lookupd_http_addresses:
        endpoint = "http://%s/delete_topic" % addr
        params = {"topic": topic}

        try:
            response = requests.get(endpoint, params=params, timeout=5)
        except (ConnectionError, Timeout) as e:
            log.err("Error making request to NSQLookupd: %s" % str(e))
        else:
            if response.status_code != requests.codes.ok:
                log.err("Failed to delete topic %s on %s: %s" %
                        (topic, endpoint, str(response)))


def _create_channel(topic, chan, lookupd_http_addresses):
    """
    Utility function which creates the requested channel
    on the specified topic for each of the given
    lookupd http addresses.
    :param topic: The name of the topic on which the channel
    will be registered.
    :type string:
    :param chan: The name of the channel to create.
    :type string:
    :param lookupd_http_adddresses: A list of address
    strings that point to `NSQLookupd` instances.
    :type list:
    """
    for addr in lookupd_http_addresses:
        # create_channel URI is deprecated bu the
        # replacement does not seem to be working
        endpoint = "http://%s/create_channel" % addr
        params = {"topic": topic, "channel": chan}

        try:
            response = requests.get(endpoint, params=params)
        except (ConnectionError, Timeout) as e:
            log.err("Error making request to NSQLookupd: %s" % str(e))
        else:
            if response.status_code != requests.codes.ok:
                log.err("Failed to create channel %s for topic %s on %s: %s" %
                        (chan, topic, endpoint, str(response)))


def _channels(topic, lookupd_http_addresses):
    """
    Utility function which lists the channels
    on the specified topic for each of the given
    lookupd http addresses.
    :param topic: The name of the topic on which the channels
    will be listed.
    :type string:
    :param lookupd_http_adddresses: A list of address
    strings that point to `NSQLookupd` instances.
    :type list:
    """
    for addr in lookupd_http_addresses:
        endpoint = "http://%s/channels" % addr
        params = {"topic": topic}

        try:
            response = requests.get(endpoint, params=params)
        except (ConnectionError, Timeout) as e:
            log.err("Error making request to NSQLookupd: %s" % str(e))
        else:
            if response.status_code != requests.codes.ok:
                log.err("Failed to list channels for topic %s on %s: %s" %
                        (topic, endpoint, str(response)))
            else:
                return response.json()["data"]["channels"]


def _delete_channel(topic, chan, lookupd_http_addresses):
    """
    Utility function which deletes the requested channel
    on the specified topic for each of the given
    lookupd http addresses.
    :param topic: The name of the topic on which the channel
    will be deleted.
    :type string:
    :param chan: The name of the channel to delete.
    :type string:
    :param lookupd_http_adddresses: A list of address
    strings that point to `NSQLookupd` instances.
    :type list:
    """
    for addr in lookupd_http_addresses:
        endpoint = "http://%s/delete_channel" % addr
        params = {"topic": topic, "channel": chan}

        try:
            response = requests.get(endpoint, params=params)
        except (ConnectionError, Timeout) as e:
            log.err("Error making request to NSQLookupd: %s" % str(e))
        else:
            if response.status_code != requests.codes.ok:
                log.err("Failed to delete channel %s for topic %s on %s: %s" %
                        (chan, topic, endpoint, str(response)))


class RemoteReadWriter(object):
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

        self._start_writer()

    def _start_writer(self):
        self._writer = nsq.Writer(self._nsqd_addresses,
                                  reconnect_interval=10.0)

    def subscribe(self, topic, callback):
        """
        Used to subscribe a callback to a topic.
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
        # Check if topic exists, if not - create it
        # Check if channel exists, if not - create it

        if not self._readers.get(topic, None):
            _create_topic(topic, self._lookupd_addresses)
            _create_channel(topic, self._server_name, self._lookupd_addresses)

            reader = nsq.Reader(message_handler=self.filter_callback(callback),
                                lookupd_http_addresses=self._lookupd_addresses,
                                topic=topic,
                                channel=self._server_name,
                                lookupd_poll_interval=5)
            self._readers[topic] = reader
            log.msg("Subscribed on %s on %s" % (topic, self._server_name))

    def filter_callback(self, callback):
        """
        Decorator function which wraps the given callback in
        a filter that discards messages which originated from this server
        instance server.

        :param callback: the callback which will be wrapped
        :type callable:
        """

        def filtered_callback(message):
            parsed_msg = json.loads(message.body)

            if parsed_msg['origin'] == self._server_name:
                message.finish()
                return True
            else:
                message.parsed_msg = parsed_msg
                return callback(message)

        return filtered_callback

    def unsubscribe(self, topic):
        """
        Unsubscribes a callback from the given topic and
        shut down the reader.

        :param topic: the topic for which to stop listening.
        :type string:
        """
        self._readers[topic].close()
        del self._readers[topic]
        log.msg("Unsubscribed from %s on %s" % (topic, self._server_name))

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
        Defaults to a logging callback.
        :type callable:
        """

        msg = dict(msg_body=msg_body, origin=self._server_name)

        def finish_pub(conn, data):
            if isinstance(data, nsq.Error):
                log.err("NSQ Error: on %s, data is %s" %
                        (conn, data))
        if not callback:
            callback = finish_pub

        self._writer.pub(topic, json.dumps(msg), callback=callback)
