##
##

import attr
import re
import logging
import os
import jinja2
import time
from typing import Optional, List, Union
from pyhostprep.command import RunShellCommand, RCNotZero
from pyhostprep.exception import FatalError
from pyhostprep import get_config_file
from pyhostprep.util import FileManager
from pyhostprep.rest import APISession
from pyhostprep.certificates import CertMgr

logger = logging.getLogger('hostprep.gateway')
logger.addHandler(logging.NullHandler())


class GatewaySetupError(FatalError):
    pass


@attr.s
class GatewayConfig:
    ip_list: Optional[List[str]] = attr.ib(default=None)
    username: Optional[str] = attr.ib(default="Administrator")
    password: Optional[str] = attr.ib(default="password")
    bucket: Optional[str] = attr.ib(default="default")
    root_path: Optional[str] = attr.ib(default="/home/sync_gateway")
    os_username: Optional[str] = attr.ib(default="sync_gateway")
    use_ssl: Optional[bool] = attr.ib(default=False)

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
               bucket: str = "default",
               root_path: str = "/home/sync_gateway",
               os_username: str = "sync_gateway",
               use_ssl: bool = False):
        return cls(
            ip_list,
            username,
            password,
            bucket,
            root_path,
            os_username,
            use_ssl
        )


class SyncGateway(object):

    def __init__(self, config: GatewayConfig):
        self.ip_list = config.ip_list
        self.username = config.username
        self.password = config.password
        self.bucket = config.bucket
        self.root_path = config.root_path
        self.os_username = config.os_username
        self.log_dir = os.path.join(self.root_path, "logs")
        self.ssl = config.use_ssl

        self.connect_ip = self.ip_list[0]

    def configure(self):
        self.prepare()

    def prepare(self, dest=None):
        if not dest:
            FileManager().make_dir(self.log_dir)
        if self.ssl:
            key_file = os.path.join(self.root_path, 'privkey.pem')
            cert_file = os.path.join(self.root_path, 'cert.pem')
            CertMgr().private_key(key_file)
            CertMgr().certificate_basic(cert_file, key_file)
            self.copy_config_file("sync_gateway_ssl.json", dest)
        else:
            self.copy_config_file("sync_gateway_3.json", dest)

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
            raise GatewaySetupError(f"can not get software version: {err}")

    def copy_config_file(self, source: str, dest: Union[str, None] = None):
        if not dest:
            dest = os.path.join(self.root_path, 'sync_gateway.json')
        src = get_config_file(source)
        with open(src, 'r') as in_file:
            input_data = in_file.read()
            in_file.close()
        env = jinja2.Environment(undefined=jinja2.DebugUndefined)
        raw_template = env.from_string(input_data)
        formatted_value = raw_template.render(
            COUCHBASE_SERVER=self.connect_ip,
            USERNAME=self.username,
            PASSWORD=self.password,
            BUCKET=self.bucket,
            ROOT_DIRECTORY=self.root_path
        )
        with open(dest, 'w') as out_file:
            out_file.write(formatted_value)
            out_file.close()

        FileManager().set_perms(dest)

    def gateway_wait(self, retry_count=300, factor=0.1):
        ssl = 1 if self.ssl else 0
        s = APISession("127.0.0.1", port=4984, ssl=ssl)
        for retry_number in range(retry_count + 1):
            try:
                result = s.api_get("/").json()
                if result.get('couchdb'):
                    return result
            except Exception as err:
                logger.debug(f"gateway_wait: waiting due to {err}")

            if retry_number == retry_count:
                return False
            logger.info(f"Waiting for gateway to initialize")
            wait = factor
            wait *= (2 ** (retry_number + 1))
            time.sleep(wait)
