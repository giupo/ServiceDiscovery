# -*- coding: utf-8 -*-

import logging
import ujson as json

import tornado.web

from ServiceDiscovery.config import config as _config

config = _config()

log = logging.getLogger(__name__)


class HealthHandler(tornado.web.RequestHandler):
    @classmethod
    def routes(cls):
        return [
            (r'/health', cls)
        ]

    def get(self):
        self.set_header('Content-type', 'text/plain; charset=utf-8')
        self.finish("OK")


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
        self.set_header('Content-type', 'text/plain; charset=utf-8')
