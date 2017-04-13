import json
import threading
import socket
import struct
import random
import logging
import base64
import uuid
import pprint
import time

try:
    from urlparse import urlparse
except:
    from urllib.parse import urlparse

from Crypto.Cipher import AES
from ServiceDiscovery.config import config
from operator import itemgetter

from twisted.internet.protocol import DatagramProtocol
# from twisted.internet import reactor

log = logging.getLogger(__name__)


class Cipher(object):
    """Base class for encoding messages"""
    def __init__(self):
        self.cipher = AES.new(
            config.get('ServiceDiscovery', 'secret'),
            AES.MODE_CFB,
            config.get('ServiceDiscovery', 'secret'))

    def encode(self, msg):
        if isinstance(msg, dict):
            msg = json.dumps(msg)
        return base64.b64encode(self.cipher.encrypt(msg))

    def decode(self, msg):
        return self.cipher.decrypt(base64.b64decode(msg))


class MultiCastTransport(object):
    """This class provides read/write itnerfaces towards a
    multicast address group"""

    def __init__(self, address, port):
        self.address = address
        self.port = int(port)

    def listen(self):
        self.sock = socket.socket(socket.AF_INET,
                                  socket.SOCK_DGRAM,
                                  socket.IPPROTO_UDP)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((self.address, self.port))
        inet = socket.inet_aton(self.address)
        mreq = struct.pack("4sl", inet, socket.INADDR_ANY)
        self.sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

    def read(self, buffersize=1024):
        "Blocking read on the multicast socket"
        if not hasattr(self, 'sock'):
            self.listen()
        return self.sock.recv(buffersize)

    def write(self, message):
        sock = socket.socket(socket.AF_INET,
                             socket.SOCK_DGRAM,
                             socket.IPPROTO_UDP)
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)

        sock.sendto(message, (self.address, self.port))


def getTransport():
    return MultiCastTransport(
        config.get('ServiceDiscovery', 'multicast_group'),
        config.getint('ServiceDiscovery', 'multicast_port'))


class ServiceHeartbeatThread(threading.Thread):
    """Sends heartbeat to the world"""

    def __init__(self, sd, gap=1 * 60):
        super(ServiceHeartbeatThread, self).__init__()
        self._sd = sd
        self.gap = gap
        self.setDaemon(True)
        self._active = False
        self._lock = threading.Lock()

    def shutdown(self):
        self.active = False
        self._sd._doHeartbeats[:] = []

    @property
    def active(self):
        self._lock.acquire()
        try:
            return self._active
        finally:
            self._lock.release()

    @active.setter
    def active(self, act):
        self._lock.acquire()
        try:
            self._active = act
        finally:
            self._lock.release()

    def run(self):
        self.active = True
        transport = getTransport()
        while self.active:
            for service in self._sd._doHeartbeats:
                if self.active:
                    service.heartbeat(transport=transport)
                else:
                    break
            time.sleep(self.gap)


# class ServiceListenerThread(threading.Thread)
class ServiceDatagramProtocol(DatagramProtocol):
    """Listenerd for messages coming from other Services"""
    def __init__(self, sd):
        self._sd = sd

    def datagramReceived(self, msg, addr):
        transport = self.transport
        myuuid = str(self._sd.id)
        try:
            log.debug("Received from <%r>: %s", addr, msg)
            cipher = Cipher()
            decoded = cipher.decode(msg)
            decoded = decoded.strip()
            data = json.loads(decoded)
            log.debug("Data received: %s", str(data))
            op = data["op"]
            if 'receiver' in data and data['receiver'] != myuuid:
                log.debug("discarding message, it wasn't for me...")

            if op == 'hi' and data['sender'] == myuuid:
                log.debug("that's an 'hi' message from "
                          "myself, discarding...")

            if op == 'hi' and data['sender'] != myuuid:
                log.debug("an 'hi' message from %s" % data['sender'])
                with self._sd._lock:
                    for serviceName, urls in self._sd.services.iteritems():
                        for url in urls:
                            msg = {
                                'op': 'Notify',
                                'sender': myuuid,
                                'receiver': data['sender'],
                                'name': serviceName,
                                'url': url,
                            }
                            
                            log.debug('sending %s' % str(msg))
                            cipher = Cipher()
                            encoded = cipher.encode(msg)
                            transport.write(encoded)
                            
            if op == "Notify" and data['receiver'] == myuuid:
                self._sd.add_service(data)
                
            if op == "QUIT" and data['receiver'] == myuuid:
                log.debug("Stop discovery...")

            if op == "Unregister":
                self._sd.remove_service(data)

            if op == "Heartbeat":
                self._sd.add_service(data)

            if op == "Register":
                self._sd.add_service(data)
                with self._sd._lock:
                    for serviceName, urls in self._sd.services.iteritems():
                        for url in urls:
                            msg = {
                                'op': 'Notify',
                                'sender': myuuid,
                                'receiver': data['sender'],
                                'name': serviceName,
                                'url': url,
                            }
                            cipher = Cipher()
                            encoded = cipher.encode(msg)
                            transport.write(encoded)

        except Exception as e:
            log.exception(e)
            log.info("Discarding and continue")


class ServiceDiscovery(object):
    """Main entry point for ServiceDiscovery"""

    def __init__(self):
        self.services = {}
        self._lock = threading.Lock()
        self.id = uuid.uuid4()
        self._doHeartbeats = []
        log.info("hi, My UUID is %s" % str(self.id))

    def register(self, service):
        log.debug("About to register service")
        msg = service.to_dict()
        msg["op"] = 'Register'
        msg['sender'] = str(self.id)
        self._send(msg)

    def unregister(self, service):
        log.debug("About to unregister service")
        msg = service.to_dict()
        msg["op"] = 'Unregister'
        msg['sender'] = str(self.id)
        self._send(msg)

    def _send(self, data):
        "Sends and encode data"
        if isinstance(data, dict):
            log.debug("about to dump: %s", data)
            data = json.dumps(data)

        cipher = Cipher()
        encoded = cipher.encode(data)
        transport = getTransport()
        transport.write(encoded)

    def hi(self):
        log.debug('called')
        data = {
            'op': 'hi',
            'sender': str(self.id)
        }
        cipher = Cipher()
        encoded = cipher.encode(data)
        transport = getTransport()
        transport.write(encoded)

    def getServices(self, key):
        """get all services of type `key`"""
        with self._lock:
            return self.services[key] if key in self.services else None

    def getService(self, key):
        """get a random service of type `key`"""
        if key in self.services:
            with self._lock:
                return random.choice(self.services[key])

    def getWeightBasedService(self, key):
        """Returns the least loaded service"""
        services = self.getService()
        if services is None:
            raise Exception("No services of type %s" % key)
        stats = []
        for base_url in services:
            # get stats
            # get base url and by convetion attach /stats
            parsed_url = urlparse(base_url)
            stats_url = "{}:{}/stats".format(
                parsed_url.scheme,
                parsed_url.netloc
            )

            # build structure to sort
            stats.append({
                'url': base_url,
                'index': stats_for_service['index']
            })

        sorted_services = sorted(stats, key=itemgetter('index'))
        return sorted_services[0]['url']

    def add_service(self, data):
        name = data["name"]
        url = data["url"]
        with self._lock:
            if name not in self.services:
                self.services[name] = [url]
            else:
                lista = self.services[name]
                if url not in lista:
                    lista.append(url)
                    lista.sort()
                    self.services[name] = lista
            log.info('services updates: \n%s' %
                     pprint.pformat(self.services))

    def remove_service(self, data):
        name = data["name"]
        url = data["url"]
        with self._lock:
            if name in self.services:
                lista = self.services[name]
                if url in lista:
                    lista.remove(url)
                    log.info('services updates: \n%s' %
                             pprint.pformat(self.services))

                # Was I in charge of its heartbeat?
                for service in self._doHeartbeats:
                    if service.url == url and service.name == name:
                        # yes! Remove it
                        self._doHeartbeats.remove(service)
                        break

                if len(lista) == 0:
                    del self.services[name]
                else:
                    self.services[name] = lista

    def scheduleForHeartBeat(self, service):
        self._doHeartbeats.append(service)

# there should be one and only one ServiceDiscovery per Process


sd = ServiceDiscovery()


class Service(object):
    """
    Hi! I'm a Service! I have a `name` and an
    `url` where you can talk with me and i can/should send heartbeats
    """
    def __init__(self, name, url, sd=sd):
        self.name = name
        self.url = url
        self.sd = sd
        self.sd.scheduleForHeartBeat(self)

    def to_json(self):
        "JSON repr of this Service"
        return json.dumps(self.to_dict())

    def to_dict(self):
        """Dict repr of this Service"""
        d = {k: v for k, v in self.__dict__.iteritems() if k != "sd"}
        return d

    def __repr__(self):
        return "<Service name:%s at %s, registered:%s>" % \
            (self.name, self.url, self.registered)

    def register(self):
        """Register the services against the ServiceDiscovery
        (should be one per process)"""
        self.sd.register(self)

    def unregister(self):
        """Unregister the services against the ServiceDiscovery"""
        self.sd.unregister(self)

    @property
    def registered(self):
        with self.sd._lock:
            services = self.sd.services
            return self.name in services and self.url in services[self.name]

    def heartbeat(self, transport=getTransport()):
        """
        Sends an heartbeat for this service
        """
        log.debug('Sending heartbeat for %s at %s' % (self.name, self.url))
        msg = self.to_dict()
        msg['op'] = 'Heartbeat'
        msg['sender'] = str(self.sd.id)

        cipher = Cipher()
        msg = cipher.encode(msg)
        transport.write(msg)


def sendHeartbeats():
    log.debug("sending heartbeats")
    transport = getTransport()
    print sd._doHeartbeats
    with sd._lock:
        for service in sd._doHeartbeats:
            service.heartbeat(transport=transport)
            
