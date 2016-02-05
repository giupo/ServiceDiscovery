import os
import json
import threading
import socket
import struct
import random
import logging
import base64
import uuid

from Crypto.Cipher import AES

log = logging.getLogger(__name__)
logging.basicConfig()
log.setLevel(logging.DEBUG)
SECRET = os.environ.get('SECRET', 'secret0000000000')
IV456 = SECRET
MCAST_GRP = '224.0.0.1'
MCAST_PORT = 5007
        

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
        inet = socket.inet_aton(MCAST_GRP)
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

class ServiceListenerThread(threading.Thread):
    def __init__(self, sd):
        super(ServiceListenerThread, self).__init__()
        self._sd = sd

    def run(self):
        self._run()
        
    def _run(self):
        transport = MultiCastTransport(MCAST_GRP, MCAST_PORT)
        while True:
            msg = transport.read()
            cipher = AES.new(SECRET, AES.MODE_CFB, IV456)
            decoded = cipher.decrypt(base64.b64decode(msg))
            decoded = decoded.strip()
            data = json.loads(decoded)
            log.debug(str(data))
            op = data["op"]
            if op == "QUIT" and data['receiver'] == str(self._sd.id):
                log.debug("Stop discovery...")
                break
            
            if op == "Unregister":
                name = data["name"]
                url = data["url"]
                with self._sd._lock:
                    if name in self._sd.services:
                        lista = self._sd.services[name]
                        lista.remove(url)
                        if len(lista) == 0:
                            del self._sd.services[name]
                        else:
                            self._sd.services[name] = lista


            if op == "Register":
                name = data["name"]
                url = data["url"]
                with self._sd._lock:
                    if name not in self._sd.services:
                        self._sd.services[name] = [ url ]
                    else:
                    
                        lista = self._sd.services[name]
                        if url not in lista:
                            lista.append(url)
                            self._sd.services[name] = lista
                            
        log.debug("Discovery over. Bye bye.")

class ServiceDiscovery(object):
    def __init__(self):
        self.services = {}
        self._lock = threading.Lock()
        self.id = uuid.uuid4()
        
    def register(self, service):
        log.debug("About to register service")
        msg = service.to_dict()
        msg["op"] = 'Register'
        msg['sender'] = str(self.id)
        self._send(json.dumps(msg))

    def unregister(self, service):
        log.debug("About to unregister service")
        msg = service.to_dict()
        msg["op"] = 'Unregister'
        msg['sender'] = str(self.id)
        self._send(json.dumps(msg))
        
    def _send(self, data):
        "Register a service"
        cipher = AES.new(SECRET, AES.MODE_CFB, IV456)
        encoded = base64.b64encode(cipher.encrypt(data))
        transport = MultiCastTransport(MCAST_GRP, MCAST_PORT)
        transport.write(encoded)
        
    @property
    def isAlive(self):
        return hasattr(self, 'listener') and self.listener.isAlive()
        
    def start(self):
        "Start discovering and registering services"
        if hasattr(self, 'listener'):
            self.stop()

        self.listener = ServiceListenerThread(self)
        self.listener.start()
        
    def stop(self):
        "Halt the discovery service"
        msg = {
            'op': 'QUIT',
            'sender': unicode(self.id),
            'receiver': unicode(self.id)
        }
        self._send(json.dumps(msg))
        
    def getServices(self, key):
        "get all services of type `key`"
        with self._lock:
            return self.services[key] if key in self.services else None
        
    def getService(self, key):
        "get a random service of type `key`"
        if key in self.services:
            with self._lock:
                return random.choice(self.services[key])

# there should be one and only one ServiceDiscovery per Process

sd = ServiceDiscovery()
sd.start()

            
class Service(object):
    """Hi! I'm a Service! I have a `name` and an
    `url` where you can talk with me"""
    def __init__(self, name, url, sd=sd):
        self.name = name
        self.url = url
        self.sd = sd
        
    def to_json(self):
        "JSON repr of this Service"
        return json.dumps(self.to_dict())

    def to_dict(self):
        "Dict repr of this Service"
        d = {k:v for k,v in self.__dict__.iteritems() if k != "sd"}
        return d

    def __repr__(self):
        return "<Service name:%s at %s, registered:%s>" % (self.name, self.url, self.registered)

    def register(self):
        "Register the services against the ServiceDiscovery (should be one per process"
        self.sd.register(self)

    def unregister(self):
        "Unregister the services against the ServiceDiscovery"
        self.sd.unregister(self)

    @property
    def registered(self):
        with self.sd._lock:
            services = self.sd.services
            return self.name in services and self.url in services[self.name]
