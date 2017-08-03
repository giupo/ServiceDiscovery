import json

import random
import logging

import consul

from config import config as _config

config = _config()

log = logging.getLogger(__name__)


class ServiceDiscovery(object):
    """Main entry point for ServiceDiscovery"""

    def __init__(self, endpoint=None):
        if endpoint is None:
            endpoint = config.get('ServiceDiscovery', 'sd')
        self.consul = consul.Client(endpoint=endpoint)

    def register(self, service):
        log.debug("About to register service: %s", service)
        r = self.consul.register(
            id=service.id, name=service.name,
            address=service.addr, port=service.port,
            tags=[service.id, 'v1'],
            check={
                'id': service.id,
                'name': "{} on {}:{}".format(
                    service.name, service.addr, service.port),
                'tcp': "{}:{}".format(service.addr, service.port),
                'interval': '30s',
                'timeout': '2s'
            })
        log.debug("Register Response: %s", r)
        
    def unregister(self, service):
        log.debug("About to unregister service: %s", service)
        self.consul.deregister(id=service.id)

    def getServices(self, key):
        """get all services of type `key`"""
        services = self.consul.info(name=key)
        return ["https://{}:{}".format(x['ServiceAddress'],
                                       x['ServicePort']) for x in services]

    def getService(self, key):
        """get a random service of type `key`"""
        services = self.getServices(key)
        return random.choice(services)


class Service(object):
    def __init__(self, name, addr, port):
        self.name = name
        self.addr = addr
        self.port = port
        self.id = "{}-{}-{}".format(name, addr, port)

    def to_json(self):
        "JSON repr of this Service"
        return json.dumps(self.to_dict())

    def to_dict(self):
        """Dict repr of this Service"""
        d = {k: v for k, v in self.__dict__.iteritems() if k != "sd"}
        return d

    def __repr__(self):
        return "<Service id:%s, name:%s, addr:%s, port:%s>" % \
            (self.id, self.name, self.addr, self.port)

