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

MCAST_GRP = '224.0.0.1'
MCAST_PORT = 5007

DEFAULT_SERVER_CERT = "../server.crt"
DEFAULT_SERVER_KEY = "../server.key"

if 'serverkey' not in options:
    define('serverkey', default=DEFAULT_SERVER_KEY,
           help='SSL key')

if 'servercert' not in options:
    define('servercert', default=DEFAULT_SERVER_CERT,
           help='SSL cert')

if 'port' not in options:
    define('port', default=7007, type=int, help="listen port")

if 'nproc' not in options:
    define('nproc', default=cpu_count()/2 or 1, type=int,
           help="Number of cores")

if 'multicast_group' not in options:
    define('multicast_group', default=MCAST_GRP, type=str,
           help='address of multicast group')

if 'multicast_port' not in options:
    define('multicast_port', default=MCAST_PORT, type=int,
           help='address of multicast port')

if 'debug' not in options:
    define('debug', default=False, type=bool)


def makeDefaultConfig():
    """builds the default config for ServiceDiscovery"""
    config = ConfigParser()
    config.add_section('ServiceDiscovery')
    config.set('ServiceDiscovery', 'multicast_group', options.multicast_group)
    config.set('ServiceDiscovery', 'multicast_port',
               str(options.multicast_port))
    config.set('ServiceDiscovery', 'nproc', str(options.nproc))
    config.set('ServiceDiscovery', 'secret',
               os.environ.get('SECRET', 'secret0000000000'))

    config.set('ServiceDiscovery', 'protocol', 'https')
    config.set('ServiceDiscovery', 'address', gethostname())
    config.set('ServiceDiscovery', 'port', str(options.port))
    config.set('ServiceDiscovery', 'servicename', 'ServiceDiscovery')

    config.set('ServiceDiscovery', 'servercert', options.servercert)
    config.set('ServiceDiscovery', 'serverkey', options.serverkey)

    return config


try:
    parse_command_line()
except Exception as e:
    log.warning(e)

config = makeDefaultConfig()
