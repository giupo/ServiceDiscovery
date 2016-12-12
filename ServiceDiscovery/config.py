# -*- coding: utf-8 -*-

import os

from socket import gethostname
from multiprocessing import cpu_count
from tornado.options import define, options, parse_command_line

try:
    from configparser import ConfigParser
except ImportError:
    from ConfigParser import ConfigParser

MCAST_GRP = '224.0.0.1'
MCAST_PORT = 5007

DEFAULT_SERVER_CERT = "/home/user/m024000/projects/grafo/server.crt"
DEFAULT_SERVER_KEY = "/home/user/m024000/projects/grafo/server.key"

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

try:
    # if called in other packages with different command line
    # handling, ignore it
    parse_command_line()
except Exception as e:
    # print it, just in case
    print str(e)
    pass


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


config = makeDefaultConfig()
