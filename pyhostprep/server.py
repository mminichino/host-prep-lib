##
##

import attr
import json
import os
import psutil
from cbcmgr.httpsessionmgr import APISession
from typing import Optional, List
from pyhostprep.network import NetworkInfo
from pyhostprep.util import FileManager
from pyhostprep.command import RunShellCommand, RCNotZero


class ClusterSetupError(Exception):
    pass


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
        if index_mem_opt == 0:
            self.index_mem_setting = "default"
        else:
            self.index_mem_setting = "memopt"

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

    def is_node(self):
        cmd = [
            "/opt/couchbase/bin/couchbase-cli", "host-list",
            "--cluster", self.rally_ip_address,
            "--username", self.username,
            "--password", self.password
        ]

        try:
            output = RunShellCommand().cmd_output(cmd, "/var/tmp", split=True, split_sep=':')
        except RCNotZero:
            return False

        for item in output:
            if item[0] == self.internal_ip:
                return True

        return False

    def is_cluster(self):
        cmd = [
            "/opt/couchbase/bin/couchbase-cli", "setting-cluster",
            "--cluster", self.rally_ip_address,
            "--username", self.username,
            "--password", self.password
        ]

        try:
            RunShellCommand().cmd_output(cmd, "/var/tmp")
        except RCNotZero:
            return False

        return True

    def node_init(self):
        if self.is_node():
            return True

        cmd = [
            "/opt/couchbase/bin/couchbase-cli", "node-init",
            "--cluster", self.rally_ip_address,
            "--username", self.username,
            "--password", self.password,
            "--node-init-hostname", self.rally_ip_address,
            "--node-init-data-path", self.data_path,
            "--node-init-index-path", self.data_path,
            "--node-init-analytics-path", self.data_path,
            "--node-init-eventing-path", self.data_path,
        ]

        try:
            RunShellCommand().cmd_output(cmd, "/var/tmp")
        except RCNotZero as err:
            raise ClusterSetupError(f"Node init failed: {err}")

        return True

    def cluster_init(self):
        self.node_init()

        cmd = [
            "/opt/couchbase/bin/couchbase-cli", "cluster-init",
            "--cluster", self.rally_ip_address,
            "--cluster-username", self.username,
            "--cluster-password", self.password,
            "--cluster-port", "8091",
            "--cluster-ramsize", self.data_quota,
            "--cluster-fts-ramsize", self.fts_quota,
            "--cluster-index-ramsize", self.index_quota,
            "--cluster-eventing-ramsize", self.eventing_quota,
            "--cluster-analytics-ramsize", self.analytics_quota,
            "--cluster-name", self.cluster_name,
            "--index-storage-setting", self.index_mem_setting,
            "--services", ','.join(self.services)
        ]

        try:
            RunShellCommand().cmd_output(cmd, "/var/tmp")
        except RCNotZero as err:
            raise ClusterSetupError(f"Cluster init failed: {err}")

        self.node_external_ip()
        self.node_change_group()

        return True

    def node_add(self):
        self.node_init()

        cmd = [
            "/opt/couchbase/bin/couchbase-cli", "server-add",
            "--cluster", self.rally_ip_address,
            "--username", self.username,
            "--password", self.password,
            "--server-add-username", self.username,
            "--server-add-password", self.password,
            "--server-add", self.internal_ip,
            "--services" ','.join(self.services)
        ]

        try:
            RunShellCommand().cmd_output(cmd, "/var/tmp")
        except RCNotZero as err:
            raise ClusterSetupError(f"Node add failed: {err}")

        self.node_external_ip()
        self.node_change_group()

        return True

    def node_external_ip(self):
        if not self.external_access:
            return True

        cmd = [
            "/opt/couchbase/bin/couchbase-cli", "setting-alternate-address",
            "--cluster", self.rally_ip_address,
            "--username", self.username,
            "--password", self.password,
            "--set",
            "--node", self.internal_ip,
            "--hostname", self.external_ip,
        ]

        try:
            RunShellCommand().cmd_output(cmd, "/var/tmp")
        except RCNotZero as err:
            raise ClusterSetupError(f"External address config failed: {err}")

        return True

    def is_group(self):
        cmd = [
            "/opt/couchbase/bin/couchbase-cli", "group-manage",
            "--cluster", self.rally_ip_address,
            "--username", self.username,
            "--password", self.password,
            "--list",
            "--group-name", self.availability_zone
        ]

        try:
            RunShellCommand().cmd_output(cmd, "/var/tmp")
        except RCNotZero:
            return False

        return True

    def create_group(self):
        cmd = [
            "/opt/couchbase/bin/couchbase-cli", "group-manage",
            "--cluster", self.rally_ip_address,
            "--username", self.username,
            "--password", self.password,
            "--create",
            "--group-name", self.availability_zone
        ]

        try:
            RunShellCommand().cmd_output(cmd, "/var/tmp")
        except RCNotZero as err:
            raise ClusterSetupError(f"Group create failed: {err}")

        return True

    def get_node_group(self):
        api = APISession(self.username, self.password)
        api.set_host(self.rally_ip_address, 0, 8091)
        response = api.api_get("/pools/default/serverGroups")

        for item in response.json().get('groups', {}):
            name = item.get('name', '')
            for node in item.get('nodes', []):
                node_ip = node.get('hostname').split(':')[0]
                if node_ip == self.internal_ip:
                    return name

        return None

    def node_change_group(self):
        current_group = self.get_node_group()
        if current_group == self.availability_zone:
            return True

        if not self.is_group():
            self.create_group()

        cmd = [
            "/opt/couchbase/bin/couchbase-cli", "group-manage",
            "--cluster", self.rally_ip_address,
            "--username", self.username,
            "--password", self.password,
            "--move-servers", self.internal_ip,
            "--from-group", current_group,
            "--to-group", self.availability_zone
        ]

        try:
            RunShellCommand().cmd_output(cmd, "/var/tmp")
        except RCNotZero as err:
            raise ClusterSetupError(f"Can not change node group: {err}")

        return True

    def rebalance(self):
        cmd = [
            "/opt/couchbase/bin/couchbase-cli", "rebalance",
            "--cluster", self.rally_ip_address,
            "--username", self.username,
            "--password", self.password,
            "--no-progress-bar"
        ]

        try:
            RunShellCommand().cmd_output(cmd, "/var/tmp")
        except RCNotZero as err:
            raise ClusterSetupError(f"Can not rebalance cluster: {err}")

        return True

    def bootstrap(self):
        if self.internal_ip == self.rally_ip_address:
            if not self.is_cluster():
                self.cluster_init()
        else:
            if not self.is_node():
                self.node_add()
