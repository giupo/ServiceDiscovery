# -*- coding: utf-8 -*-

import os
import logging
import ujson as json

import tornado.web
import tornado.ioloop
import tornado.httpserver
import tornado.gen
import tornado.httpclient
import tornado.platform.twisted
tornado.platform.twisted.install()  # noqa

from twisted.internet import reactor
from signal import signal, SIGTERM, SIGQUIT, SIGINT
try:
    from urlparse import urlparse
except:
    from urllib.parse import urlparse

from ServiceDiscovery.discovery import Service, listenMulticast
from ServiceDiscovery.config import config, showConfig
from ServiceDiscovery.stats import StatsHandler

log = logging.getLogger(__name__)


class ListServices(tornado.web.RequestHandler):

    def initialize(self):
        from ServiceDiscovery.discovery import sd
        self.sd = sd

    @classmethod
    def routes(cls):
        return [
            (r'/list/', cls),
            (r'/list', cls)
        ]
    
    def set_default_headers(self):
        # this is a JSON RESTful API
        self.set_header('Content-Type', 'application/json')

    def get(self):
        self.finish(json.dumps(self.sd.services))

        
class ServiceHandler(tornado.web.RequestHandler):
    """Handles all discovery messages via REST API"""

    def initialize(self):
        from ServiceDiscovery.discovery import sd
        self.sd = sd

    @classmethod
    def routes(cls):
        return [
            (r'/services/(.*)', cls),
            (r'/services/', cls),
            (r'/services', cls)
        ]

    def set_default_headers(self):
        # this is a JSON RESTful API
        self.set_header('Content-Type', 'application/json')

    @tornado.gen.coroutine
    def get(self, id=None):
        ret = dict()
        for service_name, urls in self.sd.services.iteritems():
            log.debug("Found %s", service_name)
            for url in urls:
                log.debug("Found %s for %s", url, service_name)
                parsed_url = urlparse(url)
                config_url = "{}://{}/{}".format(
                    parsed_url.scheme,
                    parsed_url.netloc,
                    "config")

                if parsed_url.netloc not in ret:
                    ret[parsed_url.netloc] = dict()

                if service_name not in ret[parsed_url.netloc]:
                    ret[parsed_url.netloc][service_name] = dict()
                http_client = tornado.httpclient.AsyncHTTPClient()
                try:
                    res = yield http_client.fetch(config_url,
                                                  validate_cert=False)
                    log.debug("type of body: %s", type(res.body))
                    log.debug("body: %s", res.body)
                    data = json.loads(res.body).values()[0]
                    log.debug("%s", data)
                    ret[parsed_url.netloc][service_name] = {
                        url: data
                    }
                except:
                    ret[parsed_url.netloc][service_name] = {
                        url: 'None'
                    }

        log.debug("About to return: %s", str(ret))
        self.finish(json.dumps(ret))


class ConfigHandler(tornado.web.RequestHandler):
    """Servers all config for this service"""

    @classmethod
    def routes(cls):
        return [
            (r'/config/(.*)/(.*)', cls),
            (r'/config/(.*)', cls),
            (r'/config/', cls),
            (r'/config', cls)
        ]

    def set_default_headers(self):
        # this is a JSON RESTful API
        self.set_header('Content-Type', 'application/json')

    def get(self, section=None, key=None):
        log.debug("called")
        ret = dict()
        if section is None and key is None:
            for section in config.sections():
                ret[section] = dict()
                for key, value in config.items(section):
                    ret[section][key] = value
        elif section is not None and key is None:
            ret[section] = dict()
            for key, value in config.items(section):
                ret[section][key] = value
        elif section is not None and key is not None:
            ret[section] = dict()
            ret[section] = config.get(section, key)
        else:
            raise tornado.web.HTTPError(404)
        log.debug("finished config")
        self.finish(json.dumps(ret))


# main routes registry
servicesService = None


def on_shutdown():
    """Shutdown callback"""
    global servicesService
    log.info("Shutdown started")
    if servicesService is not None:
        servicesService.unregister()
    else:
        log.warn("Servces are None!")

    reactor.fireSystemEvent('shutdown')
    reactor.disconnectAll()
    tornado.ioloop.IOLoop.instance().stop()
    log.info("Shutdown completed")


def startWebServer():
    global servicesService
    routes = []
    routes.extend(ServiceHandler.routes())
    routes.extend(ConfigHandler.routes())
    routes.extend(StatsHandler.routes())
    routes.extend(ListServices.routes())
    
    settings = {
        "cookie_secret": config.get('ServiceDiscovery', 'secret'),
        "xsrf_cookies": False
    }

    application = tornado.web.Application(routes, **settings)

    protocol = config.get('ServiceDiscovery', 'protocol')
    addr = config.get('ServiceDiscovery', 'address')
    port = config.getint('ServiceDiscovery', 'port')
    service_name = config.get('ServiceDiscovery', 'servicename')

    if protocol == "https":
        server = tornado.httpserver.HTTPServer(application, ssl_options={
            "certfile": config.get('ServiceDiscovery', 'servercert'),
            "keyfile": config.get('ServiceDiscovery', 'serverkey')
        })

    else:
        log.warning("Service Discovery Service should be on HTTPS!")
        server = tornado.httpserver.HTTPServer(application)

    while True:
        try:
            log.info('try port %s', port)
            server.bind(port, address=addr)
            log.info("%s at %s://%s:%s", service_name, protocol, addr, port)
            break
        except Exception as e:
            log.info('port %s already used (%s) ... ', str(port), str(e))
            port += 1

    config.set('ServiceDiscovery', 'port', str(port))

    servicesService = Service(service_name, "%s://%s:%s" % (
        protocol,
        addr,
        port
    ))

    # server.start(config.getint('ServiceDiscovery', 'nproc'))
    # FIXME: can't have multiprocessing with twisted ... 
    server.start(1)
    ioloop = tornado.ioloop.IOLoop.instance()
    servicesService.register()
    
    for sig in [SIGINT, SIGTERM, SIGQUIT]:
        def l(sig, frame):
            ioloop.add_callback_from_signal(on_shutdown)
        signal(sig, l)
        
    listenMulticast(ioloop)

    log.info("%s started and registered (PID: %s)", service_name, os.getpid())
    ioloop.start()

    
def main():
    showConfig()
    startWebServer()


if __name__ == '__main__':
    main()
