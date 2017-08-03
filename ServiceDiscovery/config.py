# -*- coding:utf-8 -*-

import os
import logging

from socket import gethostname
from multiprocessing import cpu_count
from tornado.options import define, options, parse_command_line
from tornado.log import enable_pretty_logging

try:
    from configparser import ConfigParser
except ImportError:
    from ConfigParser import ConfigParser


enable_pretty_logging()
log = logging.getLogger(__name__)

DEFAULT_SERVER_CERT = "server.crt"
DEFAULT_SERVER_KEY = "server.key"
DEFAULT_PORT = 7007

if 'serverkey' not in options:
    define('serverkey', default=DEFAULT_SERVER_KEY,
           help='SSL key')

if 'servercert' not in options:
    define('servercert', default=DEFAULT_SERVER_CERT,
           help='SSL cert')

if 'port' not in options:
    define('port', default=DEFAULT_PORT, type=int, help="listen port")

if 'nproc' not in options:
    define('nproc', default=cpu_count()/2 or 1, type=int,
           help="Number of cores")

if 'debug' not in options:
    define('debug', default=False, type=bool)

if 'sd' not in options:
    define('sd', default="https://{}:{}/services".format(
        gethostname(), DEFAULT_PORT),
           type=str)

if 'registryHost' not in options:
    define("registryHost", default="localhost",
           help="Redis host")
    
if 'registryPort' not in options:
    define("registryPort", default=6379, type=int, help="Redis port")
                    

def makeDefaultConfig():
    """builds the default config for ServiceDiscovery"""
    config = ConfigParser()
    config.add_section('ServiceDiscovery')
    config.set('ServiceDiscovery', 'nproc', str(options.nproc))
    config.set('ServiceDiscovery', 'secret',
               os.environ.get('SECRET', 'secret0000000000'))

    config.set('ServiceDiscovery', 'protocol', 'https')
    config.set('ServiceDiscovery', 'address', gethostname())
    config.set('ServiceDiscovery', 'port', str(options.port))
    config.set('ServiceDiscovery', 'servicename', 'ServiceDiscovery')

    config.set('ServiceDiscovery', 'servercert', options.servercert)
    config.set('ServiceDiscovery', 'serverkey', options.serverkey)
    config.set('ServiceDiscovery', 'sd', options.sd)
    
    config.set('ServiceDiscovery', 'registryHost', options.registryHost)
    config.set('ServiceDiscovery', 'registryPort', str(options.registryPort))
    
    log.info("Rebuilt config")
    for section in config.sections():
        for key, value in config.items(section):
            log.info("[%s] %s = %s", section, key, value)
    return config


_config = None


def config():
    global _config
    if _config is None:
        parse_command_line()
        _config = makeDefaultConfig()
    return _config
