"""Consul Service Discovery API


Examples:
    import consul
    service = consul.Client()
    service.register(id='flexlm1', name='flexlm',
                address='10.112.0.211', port=28518,
                tags=('flexlm1', light', 'v1'),
                check={'id': 'flexlm', 'name': 'flexlm on port 28518',
                       'tcp': '10.112.0.211:28518',
                       'Interval': '30s', 'timeout': '2s'})
    service.deregister(id='flexlm1')
    service.list()
    service.info(name='flexlm')

The registration/deregistration is done using the consul agent API:
    http://localhost:8500
    PUT /v1/agent/service/register
    DELETE /v1/agent/service/deregister/<serviceId>

To query the information the catalog API is used:
    http://localhost:8500
    GET /v1/catalog/services
    GET /v1/catalog/service/bigdata
    GET /v1/catalog/nodes
    GET /v1/catalog/node/c13-9

The payload for the registration request has the following format:
{
  "ID": "flexlm1",
  "Name": "flexlm",
  "Tags": ["flexlm1", light", "v1"],
  "Address": "10.112.0.211",
  "Port": 28518,
  "Check": {
    "id": "flexlm",
    "name": "flexlm on port 28518",
    "tcp": "10.112.0.211:28518",
    "Interval": "30s",
    "timeout": "2s"
  }
}

"""

import requests
import logging

log = logging.getLogger(__name__)


class Client(object):
    """Service Discovery Client to perform basic operations

    Examples:

        import consul
        service = consul.Client()
        service.register(id='flexlm1', name='flexlm',
                    address='10.112.0.211', port=28518,
                    tags=('flexlm1', light', 'v1'))
        service.deregister(id='flexlm1')
        service.list()
        service.info(name='flexlm')

    The service can also be registered with an associated check:

        service.register(id='flexlm1', name='flexlm',
                    address='10.112.0.211', port=28518,
                    tags=('flexlm1', light', 'v1'),
                    check={'id': 'flexlm', 'name': 'flexlm on port 28518',
                           'tcp': '10.112.0.211:28518',
                           'Interval': '30s', 'timeout': '2s'})

    The registration/deregistration is done using the consul agent API:

        PUT /v1/agent/service/register
        DELETE /v1/agent/service/deregister/<serviceId>
    """

    def __init__(self, endpoint='http://localhost:8500'):
        self.endpoint = endpoint
        # self.url_register = '{}/{}'.format(
        #  self.endpoint, 'v1/agent/service/register')
        # self.url_deregister = '{}/{}'.format(
        #  self.endpoint, 'v1/agent/service/deregister')
        self.url_register = '{}/{}'.format(
            self.endpoint, 'v1/catalog/register')
        self.url_deregister = '{}/{}'.format(
            self.endpoint, 'v1/catalog/deregister')
        self.url_services = '{}/{}'.format(
            self.endpoint, 'v1/catalog/services')
        self.url_service = '{}/{}'.format(self.endpoint, 'v1/catalog/service')
        self.url_nodes = '{}/{}'.format(self.endpoint, 'v1/catalog/nodes')
        self.url_node = '{}/{}'.format(self.endpoint, 'v1/catalog/node')
        self.url_check_register = '{}/{}'.format(
            self.endpoint, 'v1/agent/check/register')

    def register(self, node, address, datacenter=None,
                 taggedaddresses=None, nodemeta=None,
                 Service=None, Check=None):
        """Register a new service with the local consul agent"""
        service = {
            'Node': node,
            'Address': address,
        }

        if datacenter:
            service['Datacenter'] = datacenter
        
        if taggedaddresses:
            service['TaggedAddresses'] = taggedaddresses

        if Service:
            service['Service'] = Service

        # if Check:
        #    service['Check'] = Check

        r = requests.put(self.url_register, json=service)
        if r.status_code != 200:
            log.debug('response.text: %s', r.text)
            raise consulRegistrationError(
                'PUT returned {}'.format(r.status_code))

        if Check:
            r = requests.put(self.url_check_register, json=Check)
            if r.status_code != 200:
                log.debug('response.text: %s', r.text)
                raise consulRegistrationError(
                    'PUT returned {}'.format(r.status_code))

        return r

    def deregister(self, node, datacenter="", CheckID=None, ServiceID=None):
        """Deregister a service with the local consul agent"""

        payload = {
            'Node': node,
            'Datacenter': datacenter
        }

        if CheckID:
            payload['CheckID'] = CheckID
        if ServiceID:
            payload['ServiceID'] = ServiceID

        r = requests.put(self.url_deregister, json=payload)
        if r.status_code != 200:
            raise consulDeregistrationError(
                'PUT returned {}'.format(r.status_code))
        return r

    def list(self):
        """List all services that have been registered"""
        r = requests.get(self.url_services)
        return r.json()

    def info(self, name):
        """Info about a given service"""
        r = requests.get('{}/{}'.format(self.url_service, name))
        return r.json()


class consulRegistrationError(Exception):
    pass


class consulDeregistrationError(Exception):
    pass
