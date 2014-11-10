import logging
from zope.interface import implements

from twisted.cred import credentials, strcred
from twisted.python import usage, log
from twisted.plugin import IPlugin
from twisted.application.service import IServiceMaker

import ircdd.server as ircdd_server
from ircdd import context

from tornado.platform.twisted import TwistedIOLoop
TwistedIOLoop().install()

logging.basicConfig()
observer = log.PythonLoggingObserver()
observer.start()


class Options(usage.Options, strcred.AuthOptionMixin):
    supportedInterfaces = (credentials.IUsernamePassword)

    optParameters = [
        ["hostname", "H", "127.0.0.1", "The name of this instance."],
        ["port", "P", 5799, "Port on which to listen for client connections."],
        ["db", "D", "ircdd", "Name of the database holding cluster data."],
        ["rdb_port", "", 28015, "Database port for client connections."],
        ["rdb_host", "", "localhost", "Database host."],
        ["config", "C", None, "Configuration file."]
        ]

    optFlags = [["ssl", "S", "Use ssl."],
                ["verbose", "V", "Log verbose output."],
                ["group_on_request", "G", "Create groups on request."],
                ["user_on_request", "U", "Create users on request."]]

    def __init__(self):
        usage.Options.__init__(self)
        self['nsqd_tcp_address'] = []
        self['lookupd_http_address'] = []

    def opt_nsqd_tcp_address(self, address):
        self['nsqd_tcp_address'].append(address)

    def opt_lookupd_http_address(self, address):
        self['lookupd_http_address'].append(address)


class IRCDDServiceMaker():
    implements(IServiceMaker, IPlugin)
    tapname = 'ircdd'
    description = 'Distributed IRC Daemon'
    options = Options

    def makeService(self, config):
        ctx = context.makeContext(config)
        return ircdd_server.makeServer(ctx)

serviceMaker = IRCDDServiceMaker()
