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
if 'port' not in options:
    define('port', default=7007, type=int, help="listen port")
if 'nproc' not in options:
    define('nproc', default=cpu_count()/2 or 1, type=int,
           help="Number of cores")

define('multicast_group', default=MCAST_GRP, type=str,
       help='address of multicast group')
define('multicast_port', default=MCAST_PORT, type=int,
       help='address of multicast port')

parse_command_line()


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

    config.set('ServiceDiscovery', 'protocol', 'http')
    config.set('ServiceDiscovery', 'address', gethostname())
    config.set('ServiceDiscovery', 'port', str(options.port))
    config.set('ServiceDiscovery', 'servicename', 'ServiceDiscovery')
    return config


config = makeDefaultConfig()
