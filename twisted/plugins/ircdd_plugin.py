from zope.interface import implements

from twisted.cred import credentials, strcred
from twisted.python import usage, log
from twisted.plugin import IPlugin
from twisted.application.service import IServiceMaker

import ircdd.server as ircdd_server
from ircdd import context


class Options(usage.Options, strcred.AuthOptionMixin):
    supportedInterfaces = (credentials.IUsernamePassword)

    optParameters = [
        ['host', 'h', 'localhost'],
        ['port', 'p', 5799],
        ]

    optFlags = [['ssl', 's'], ['verbose', 'v']]

    def __init__(self):
        usage.Options.__init__(self)
        self['nsqd_tcp_addresses'] = []
        self['lookupd_http_addresses'] = []

    def opt_nsqd_tcp_addresses(self, address):
        self['nsqd_tcp_addresses'].append(address)

    def opt_lookupd_http_addresses(self, address):
        self['lookupd_http_addresses'].append(address)


class IRCDDServiceMaker():
    implements(IServiceMaker, IPlugin)
    tapname = 'ircdd'
    description = 'Distributed IRC Daemon'
    options = Options

    def makeService(self, config):
        ctx = context.makeContext(config)
        return ircdd_server.makeServer(ctx)

serviceMaker = IRCDDServiceMaker()
