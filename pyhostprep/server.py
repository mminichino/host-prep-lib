##
##

import attr
import psutil
from enum import Enum
from cbcmgr.httpsessionmgr import APISession
from typing import Optional, List, Sequence
from pyhostprep.network import NetworkInfo
from pyhostprep.command import RunShellCommand, RCNotZero
from pyhostprep.retry import retry


class ClusterSetupError(Exception):
    pass


class IndexMemoryOption(Enum):
    default = 0
    memopt = 1


@attr.s
class ServerConfig:
    name: Optional[str] = attr.ib(default=None)
    ip_list: Optional[List[str]] = attr.ib(default=None)
    services: Optional[Sequence[str]] = attr.ib(default=("data", "index", "query"))
    username: Optional[str] = attr.ib(default="Administrator")
    password: Optional[str] = attr.ib(default="password")
    index_mem_opt: Optional[IndexMemoryOption] = attr.ib(default=IndexMemoryOption.default)
    availability_zone: Optional[str] = attr.ib(default="primary")
    data_path: Optional[str] = attr.ib(default="/opt/couchbase/var/lib/couchbase/data")

    @property
    def get_values(self):
        return self.__annotations__

    @property
    def as_dict(self):
        return self.__dict__

    @classmethod
    def create(cls,
               name: str,
               ip_list: List[str],
               services: Sequence[str] = ("data", "index", "query"),
               username: str = "Administrator",
               password: str = "password",
               index_mem_opt: IndexMemoryOption = IndexMemoryOption.default,
               availability_zone: str = "primary",
               data_path: str = "/opt/couchbase/var/lib/couchbase/data"):
        return cls(
            name,
            ip_list,
            services,
            username,
            password,
            index_mem_opt,
            availability_zone,
            data_path
        )


class CouchbaseServer(object):

    def __init__(self, config: ServerConfig):
        self.cluster_name = config.name
        self.ip_list = config.ip_list
        self.username = config.username
        self.password = config.password
        self.data_path = config.data_path
        self.index_mem_opt = config.index_mem_opt
        self.availability_zone = config.availability_zone
        self.services = config.services

        self.rally_ip_address = self.ip_list[0]
        self.data_quota = None
        self.analytics_quota = None
        self.index_quota = None
        self.fts_quota = None
        self.eventing_quota = None
        self.internal_ip, self.external_ip, self.external_access = self.get_net_config()
        self.get_mem_config()

    def get_mem_config(self):
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
            reservation += _index_mem

        memory_pool = total_mem - reservation

        if "analytics" in self.services and "data" in self.services:
            analytics_pool = int(memory_pool / 5)
            analytics_quota = analytics_pool if analytics_pool > _analytics_mem else _analytics_mem
        elif "analytics" in self.services:
            analytics_quota = memory_pool
        else:
            analytics_quota = _analytics_mem

        if "data" in self.services and "analytics" in self.services:
            data_quota = memory_pool - analytics_quota
        elif "data" in self.services:
            data_quota = memory_pool
        else:
            data_quota = _data_mem
                
        self.eventing_quota = str(_eventing_mem)
        self.fts_quota = str(_fts_mem)
        self.index_quota = str(_index_mem)
        self.analytics_quota = str(analytics_quota)
        self.data_quota = str(data_quota)

    def get_net_config(self):
        if self.rally_ip_address == "127.0.0.1":
            internal_ip = "127.0.0.1"
            external_ip = None
            external_access = False
        else:
            internal_ip = NetworkInfo().get_ip_address()
            external_ip = NetworkInfo().get_pubic_ip_address()
            external_access = NetworkInfo().check_port(external_ip, 8091)
        return internal_ip, external_ip, external_access

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
            "--index-storage-setting", self.index_mem_opt.name,
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

    @retry()
    def cluster_wait(self):
        cmd = [
            "/opt/couchbase/bin/couchbase-cli", "server-list",
            "--cluster", self.rally_ip_address,
            "--username", self.username,
            "--password", self.password,
        ]
        RunShellCommand().cmd_output(cmd, "/var/tmp")

    def bootstrap(self):
        if self.internal_ip == self.rally_ip_address:
            if not self.is_cluster():
                self.cluster_init()
        else:
            if not self.is_node():
                self.node_add()
