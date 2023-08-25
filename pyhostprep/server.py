##
##

import attr
import json
import os
import psutil
from typing import Optional, List
from pyhostprep.network import NetworkInfo
from pyhostprep.util import FileManager


@attr.s
class ServerConfig:
    internal_ip: Optional[str] = attr.ib(default=None)
    external_ip: Optional[str] = attr.ib(default=None)
    services: Optional[List[str]] = attr.ib(default=None)
    index_mem_opt: Optional[int] = attr.ib(default=None)
    availability_zone: Optional[str] = attr.ib(default=None)
    data_path: Optional[str] = attr.ib(default=None)

    @property
    def get_values(self):
        return self.__annotations__

    @property
    def as_dict(self):
        return self.__dict__

    @classmethod
    def from_dict(cls, json_data: dict):
        return cls(
            json_data.get("internal_ip"),
            json_data.get("external_ip"),
            json_data.get("services", []),
            json_data.get("index_mem_opt"),
            json_data.get("availability_zone"),
            json_data.get("data_path"),
        )


class CouchbaseServer(object):

    def __init__(self,
                 name: str,
                 ip_list: list[str],
                 services: list[str] = None,
                 username: str = "Administrator",
                 password: str = "password",
                 index_mem_opt: int = 0,
                 availability_zone: str = "primary",
                 data_path: str = "/opt/couchbase/var/lib/couchbase/data"):
        self.data_quota = None
        self.analytics_quota = None
        self.index_quota = None
        self.fts_quota = None
        self.eventing_quota = None
        self.config_dir = "/etc/couchbase"
        self.config_file = "cbs_node.cfg"
        self.internal_ip, self.external_ip, self.external_access = self.get_net_config()
        self.ip_list = ip_list
        self.rally_ip_address = self.ip_list[0]
        self.get_mem_config()
        self.cluster_name = name
        self.username = username
        self.password = password
        self.data_path = data_path
        self.index_mem_opt = index_mem_opt
        self.availability_zone = availability_zone
        if not services:
            self.services = ["data", "index", "query"]
        else:
            self.services = services

        self.config = ServerConfig().from_dict(dict(
                internal_ip=self.internal_ip,
                external_ip=self.external_ip if self.external_access else None,
                services=self.services,
                index_mem_opt=self.index_mem_opt,
                availability_zone=self.availability_zone,
                data_path=self.data_path
            ))
        self.write_config()

    def get_mem_config(self):
        analytics_quota = 0
        data_quota = 0
        host_mem = psutil.virtual_memory()
        total_mem = int(host_mem.total / (1024 * 1024))
        _eventing_mem = 256
        _fts_mem = 2048
        if self.index_mem_opt == 0:
            _index_mem = 512
        else:
            _index_mem = 1024
        _analytics_mem = 1024
        _data_mem = 2048

        os_pool = int(total_mem * 0.3)
        reservation = 2048 if os_pool < 2048 else 4096 if os_pool > 4096 else os_pool
        
        if "eventing" in self.services:
            reservation += _eventing_mem
        if "fts" in self.services:
            reservation += _fts_mem
        if "index" in self.services:
            reservation += self.services

        memory_pool = total_mem - reservation

        if "analytics" in self.services:
            if "data" in self.services:
                analytics_pool = int(memory_pool / 5)
                analytics_quota = analytics_pool if analytics_pool > _analytics_mem else _analytics_mem
            else:
                analytics_quota = memory_pool

        if "data" in self.services:
            if "analytics" in self.services:
                data_quota = memory_pool - analytics_quota
            else:
                data_quota = memory_pool
                
        self.eventing_quota = _eventing_mem
        self.fts_quota = _fts_mem
        self.index_quota = _index_mem
        self.analytics_quota = analytics_quota
        self.data_quota = data_quota

    @staticmethod
    def get_net_config():
        internal_ip = NetworkInfo().get_ip_address()
        external_ip = NetworkInfo().get_pubic_ip_address()
        external_access = NetworkInfo().check_port(external_ip, 8091)
        return internal_ip, external_ip, external_access

    def write_config(self):
        config_file = os.path.join(self.config_dir, self.config_file)
        FileManager().make_dir(self.config_dir)
        with open(config_file, 'w') as cfg_file:
            json.dump(self.config.as_dict, cfg_file)
            cfg_file.write('\n')
            cfg_file.close()

    def read_config(self):
        config_file = os.path.join(self.config_dir, self.config_file)
        with open(config_file, 'r') as cfg_file:
            self.config.from_dict(json.load(cfg_file))
        return self.config

    def cfg_file_exists(self):
        return os.path.exists(os.path.join(self.config_dir, self.config_file))

    def is_node(self, ip_address: str):
        cmd = [
            "/opt/couchbase/bin/couchbase-cli", "host-list",
            "--cluster", self.rally_ip_address,
            "--username", self.username,
            "--password", self.password
        ]

    def cb_node_init(self):
        pass
