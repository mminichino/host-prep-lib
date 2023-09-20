##
##

import attr
import psutil
import logging
import socket
import time
from enum import Enum
from cbcmgr.httpsessionmgr import APISession
from typing import Optional, List, Sequence
from pyhostprep.network import NetworkInfo
from pyhostprep.command import RunShellCommand, RCNotZero
from pyhostprep.exception import FatalError
from pyhostprep import get_config_file

logger = logging.getLogger('hostprep.gateway')
logger.addHandler(logging.NullHandler())


class GatewaySetupError(FatalError):
    pass


@attr.s
class GatewayConfig:
    ip_list: Optional[List[str]] = attr.ib(default=None)
    username: Optional[str] = attr.ib(default="Administrator")
    password: Optional[str] = attr.ib(default="password")
    root_path: Optional[str] = attr.ib(default="/home/sync_gateway")

    @property
    def get_values(self):
        return self.__annotations__

    @property
    def as_dict(self):
        return self.__dict__

    @classmethod
    def create(cls,
               ip_list: List[str],
               username: str = "Administrator",
               password: str = "password",
               root_path: str = "/home/sync_gateway"):
        return cls(
            ip_list,
            username,
            password,
            root_path
        )


class SyncGateway(object):

    def __init__(self, config: GatewayConfig):
        self.ip_list = config.ip_list
        self.username = config.username
        self.password = config.password
        self.root_path = config.root_path

        self.connect_ip = self.ip_list[0]

    def get_version(self):
        cmd = [
            '/opt/couchbase-sync-gateway/bin/sync_gateway',
            '-help'
        ]

        try:
            result = RunShellCommand().cmd_output(cmd, self.root_path)
            print(result)
        except RCNotZero as err:
            raise GatewaySetupError(f"ca not get software version: {err}")

    def copy_config_file(self):
        pass
