##
##

import attr
import re
import logging
import os
import jinja2
from typing import Optional, List
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

    def configure(self):
        sw_version = self.get_version()

        if sw_version and sw_version == "3":
            self.copy_config_file("sync_gateway_3.json")
        else:
            self.copy_config_file("sync_gateway_2.json")

    def get_version(self):
        cmd = [
            '/opt/couchbase-sync-gateway/bin/sync_gateway',
            '-help'
        ]

        try:
            result = RunShellCommand().cmd_output(cmd, self.root_path)
            pattern = r"^.*/([0-9])\.[0-9]\.[0-9].*$"
            match = re.search(pattern, result[0])
            if match and len(match.groups()) > 0:
                return match.group(1)
            else:
                return None
        except RCNotZero as err:
            raise GatewaySetupError(f"ca not get software version: {err}")

    def copy_config_file(self, source: str):
        dest = os.path.join(self.root_path, 'sync_gateway.json')
        src = get_config_file(source)
        with open(src, 'r') as in_file:
            input_data = in_file.read()
            in_file.close()
        env = jinja2.Environment(undefined=jinja2.DebugUndefined)
        raw_template = env.from_string(input_data)
        formatted_value = raw_template.render(
            COUCHBASE_SERVER=self.connect_ip,
            NODE_ZONE=self.username,
            SERVICES=self.password
        )
        print(formatted_value)
