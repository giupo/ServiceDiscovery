import json
import requests
import random
import logging

import consul

from ServiceDiscovery.config import config as _config

config = _config()

log = logging.getLogger(__name__)


class ServiceDiscovery(object):
    """Main entry point for ServiceDiscovery"""

    def __init__(self, endpoint=None):
        if endpoint is None:
            endpoint = config.get('ServiceDiscovery', 'sd')
        self.consul = consul.Client(endpoint=endpoint)
        self.services = {}

    def _refresh(self):
        log.info("Refreshing Service definitions")
        self.services = {
            k: self.consul.info(k)
            for k in self.consul.list().keys()
        }

    def register(self, service, datacenter=None, check=None, tags=None):
        log.debug("About to register service: %s", service)
        Node = service.node
        if check is None:
            log.debug('setting default check for %s based on TCP %s:%s ',
                      service.name, service.addr, service.port)
            check = {
                # 'ServiceID': service.id,
                'Node': Node,
                'Name': "{} on {}:{}".format(
                    service.name, service.addr, service.port),
                'Tcp': "{}:{}".format(service.addr, service.port),
                'Interval': '30s',
                'Timeout': '2s',
                # 'Status': 'passing'
            }
        else:
            log.debug('setting custom check for %s: %s', service.name, check)

        if tags is None:
            tags = [service.id, 'v1']

        # Address = service.addr
        serviceRepr = service.consulRepr()
        serviceRepr['Tags'] = tags
        
        r = self.consul.register(
            id=service.id,
            address=service.addr,
            port=service.port,
            name=service.name,
            check=check)

        log.debug("Register Response: %s", r)
        
    def unregister(self, service):
        log.debug("About to unregister service: %s", service)
        self.consul.deregister(id=service.id)

    def getServices(self, key):
        """get all services of type `key`"""
        if key not in self.services:
            self._refresh()
            if key not in self.services:
                return []
        
        services = self.services[key]
        log.debug("%s", services)
        return [
            "https://{}:{}".format(
                x['ServiceAddress'],
                x['ServicePort'])
            for x in services
        ]

    def getService(self, key):
        """get a random service of type `key`"""
        services = self.getServices(key)
        return random.choice(services)

    def call(self, key, path, ck_health=True, **kwargs):
        base_url = self.getService(key)
        retries = 10
        while retries:
            if ck_health:
                res = requests.get(base_url + "/health", **kwargs)
                if res.status_code != 200:
                    # handle it
                    self._refresh()
                    services = self._services[key]
                    
                    retries -= 1
                    
                
            url = "".join(base_url, path)
            res = requests.get(url, **kwargs)
            return res.json()
        

class Service(object):
    def __init__(self, name, addr, port, node=None):
        self.name = name
        self.addr = addr
        if node is None:
            node = addr.split('.')[0]
        self.node = node
        self.port = port
        self.id = "{}-{}-{}".format(self.name, self.node, self.port)

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

    def consulRepr(self):
        return {
            'ID': self.id,
            'Node': self.node,
            'Service': self.name,
            'Address': self.addr,
            'Port': int(self.port)
        }
