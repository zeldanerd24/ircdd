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
        ["hostname", "H", "127.0.0.1"],
        ["port", "P", 5799],
        ["db", "D", "ircdd"],
        ["rdb_port", "", 28015],
        ["rdb_hostname", "", "127.0.0.1"],
        ]

    optFlags = [["ssl", "S"],
                ["verbose", "V"],
                ["group_on_request", "G"],
                ["user_on_request", "U"]]

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
