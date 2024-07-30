##
##

import os
import re
import attr
import psutil
import logging
import socket
import time
import configparser
from pathlib import Path
from functools import cmp_to_key
from enum import Enum
from itertools import zip_longest
from pyhostprep.httpsessionmgr import APISession
from typing import Optional, List, Sequence
from pyhostprep.network import NetworkInfo
from pyhostprep.command import RunShellCommand, RCNotZero
from pyhostprep.exception import FatalError
from pyhostprep.util import FileManager
from pyhostprep.osfamily import OSFamily
from pyhostprep.osinfo import OSRelease
from pyhostprep.certificates import CertMgr

logger = logging.getLogger('hostprep.server')
logger.addHandler(logging.NullHandler())
CONFIG_DIR = os.path.join(Path.home(), '.swmgr')
CONFIG_FILE = os.path.join(CONFIG_DIR, 'server.cfg')


def service_cmp(a, b):
    if a[2] == b[2]:
        return 0
    if a[2] is not None and (a[2] == 'default' or re.search('data', a[2])):
        return -1
    if b[2] is not None and (b[2] == 'default' or re.search('data', b[2])):
        return 1
    else:
        return 0


class ClusterSetupError(FatalError):
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
    host_list: Optional[List[str]] = attr.ib(default=None)
    service_list: Optional[List[str]] = attr.ib(default=None)
    index_mem_opt: Optional[IndexMemoryOption] = attr.ib(default=IndexMemoryOption.default)
    availability_zone: Optional[str] = attr.ib(default="primary")
    data_path: Optional[str] = attr.ib(default="/opt/couchbase/var/lib/couchbase/data")
    community_edition: Optional[bool] = attr.ib(default=False)
    private_key: Optional[str] = attr.ib(default=None)

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
               host_list=None,
               service_list=None,
               index_mem_opt: IndexMemoryOption = IndexMemoryOption.default,
               availability_zone: str = "primary",
               data_path: str = "/opt/couchbase/var/lib/couchbase/data",
               community_edition: bool = False,
               private_key: str = None):
        if host_list is None:
            host_list = []
        return cls(
            name,
            ip_list,
            services,
            username,
            password,
            host_list,
            service_list,
            index_mem_opt,
            availability_zone,
            data_path,
            community_edition,
            private_key
        )


class CouchbaseServer(object):

    def __init__(self, config: ServerConfig):
        self._init_complete = False
        self.config_data = configparser.ConfigParser()
        self.cluster_name = config.name
        ip_list = config.ip_list
        service_list = config.service_list if config.service_list is not None else []
        self.username = config.username
        self.password = config.password
        host_list = config.host_list if config.host_list is not None else []
        self.data_path = config.data_path
        self.index_mem_opt = config.index_mem_opt
        self.availability_zone = config.availability_zone
        self.community_edition = config.community_edition
        self.private_key = config.private_key if config.private_key and config.private_key != 'null' else None

        if OSRelease().family == OSFamily.LINUX:
            self.ca_path = r"/opt/couchbase/var/lib/couchbase/inbox/CA"
        elif OSRelease().family == OSFamily.WINDOWS:
            self.ca_path = r"C:\Program Files\couchbase\server\var\lib\couchbase\inbox\CA"
        elif OSRelease().family == OSFamily.MACOS:
            self.ca_path = r"/Applications/Couchbase Server.app/Contents/Resources/couchbase-core/var/lib/couchbase/inbox/CA"
        else:
            raise ClusterSetupError(f"Unknown OS type")

        try:
            FileManager().make_dir(CONFIG_DIR)
            self.config_data.read(CONFIG_FILE)
        except Exception as e:
            message = f"Failed to make config directory {CONFIG_DIR}: {e}"
            raise ClusterSetupError(message)

        self.ip_list, self.host_list, self.service_list = self.create_node_lists(ip_list, host_list, service_list)

        self.data_quota = None
        self.analytics_quota = None
        self.index_quota = None
        self.fts_quota = None
        self.eventing_quota = None
        self.internal_ip, self.external_ip, self.external_access, self.rally_ip_address, self.node_index = self.get_net_config()

        try:
            _services_entry = self.service_list[self.node_index].split(',')
            _services = _services_entry if _services_entry != ["default"] else ["data", "index", "query"]
        except IndexError:
            _services = config.services if config.services != ["default"] else ["data", "index", "query"]

        self.services = ["fts" if e == "search" else e for e in _services]
        self.get_mem_config()

        self.rally_ip_address = self.read_config()

        logger.info(f"Member list: {','.join(self.ip_list)}")
        logger.info(f"Host list: {','.join(self.host_list) if len(self.host_list) > 0 else 'None'}")
        logger.info(f"Service list: {':'.join(self.service_list) if len(self.service_list) > 0 else 'None'}")
        logger.info(f"Internal IP: {self.internal_ip}")
        logger.info(f"External IP: {self.external_ip}")
        logger.info(f"External Access: {self.external_access}")
        logger.info(f"Rally Host: {self.rally_ip_address}")
        logger.info(f"Services: {self.config_data.get('cluster', 'services', fallback=','.join(self.services))}")

        self.admin_port = 8091
        if not self.wait_port(self.internal_ip, self.admin_port):
            logger.error(f"Can not connect to admin port on this host ({self.internal_ip})")
            raise ClusterSetupError(f"Host {self.internal_ip}:{self.admin_port} is not reachable")
        if not self.wait_port(self.rally_ip_address, self.admin_port):
            logger.error(f"Can not connect to admin port on rally node {self.rally_ip_address}")
            raise ClusterSetupError(f"Host {self.rally_ip_address}:{self.admin_port} is not reachable")

        self._init_complete = True

    def __del__(self):
        if self._init_complete:
            logger.info("Done.")
            self.write_config()

    def read_config(self):
        return self.config_data.get('cluster', 'rally_ip_address', fallback=self.rally_ip_address)

    def write_config(self):
        try:
            self.config_data.set('cluster', 'rally_ip_address', self.rally_ip_address)
        except configparser.NoSectionError:
            self.config_data['cluster'] = dict(rally_ip_address=self.rally_ip_address)
        with open(CONFIG_FILE, 'w') as configfile:
            self.config_data.write(configfile)

    @staticmethod
    def create_node_lists(ip_list, host_list, service_list):
        service_cmp_key = cmp_to_key(service_cmp)
        result = list(zip_longest(ip_list, host_list, service_list))
        result.sort(key=service_cmp_key)

        _ip_list = [e[0] for e in result if e[0] is not None]
        _host_list = [e[1] for e in result if e[1] is not None]
        _service_list = [e[2] for e in result if e[2] is not None]

        return _ip_list, _host_list, _service_list

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
        if self.ip_list[0] == "127.0.0.1":
            internal_ip = rally_address = "127.0.0.1"
            external_ip = None
            external_access = False
            my_index = 0
        elif self.host_list and len(self.host_list) > 0:
            internal_address = NetworkInfo().get_ip_address()
            my_index = self.ip_list.index(internal_address)
            internal_ip = self.host_list[my_index]
            external_ip = None
            external_access = False
            rally_address = self.host_list[0]
            for (ip_address, hostname) in zip(self.ip_list, self.host_list):
                host_file = '/etc/hosts'
                entry_string = f"{ip_address} {hostname}"
                if not FileManager().file_search(host_file, entry_string):
                    FileManager().file_append(host_file, entry_string)
        else:
            external_ip = NetworkInfo().get_pubic_ip_address()
            internal_ip = NetworkInfo().get_ip_address()
            my_index = self.ip_list.index(internal_ip)
            external_access = NetworkInfo().check_port(external_ip, 8091)
            rally_address = self.ip_list[0]

        return internal_ip, external_ip, external_access, rally_address, my_index

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

    def cluster_ca_load(self):
        home_dir = FileManager().get_user_home()
        ca_key = os.path.join(home_dir, "ca.key")
        ca_cert = os.path.join(home_dir, "ca.pem")
        if os.path.exists(ca_key) and os.path.exists(ca_cert):
            ca_cert_file = os.path.join(self.ca_path, "ca.pem")
            ca_key_file = os.path.join(os.path.dirname(self.ca_path), "ca.key")
            FileManager().make_dir(self.ca_path, "couchbase", "couchbase", mode=0o700)
            FileManager().copy_file(ca_key, ca_key_file, "couchbase", "couchbase", mode=0o600)
            FileManager().copy_file(ca_cert, ca_cert_file, "couchbase", "couchbase", mode=0o600)

            api = APISession(self.username, self.password)
            api.set_host(self.internal_ip, 0, 8091)

            logger.info(f"Loading cluster certificate authority")

            response = api.api_empty_post("/node/controller/loadTrustedCAs")
            result = response.json()

            if not isinstance(result, list) or result[0].get("id") != 1:
                logger.error(f"Failed to load CA: response: {response.json()}")
                raise ClusterSetupError(f"CA load failed")

        return True

    def host_cert_load(self):
        home_dir = FileManager().get_user_home()
        ca_key = os.path.join(home_dir, "ca.key")
        ca_cert = os.path.join(home_dir, "ca.pem")
        if os.path.exists(ca_key) and os.path.exists(ca_cert):
            FileManager().make_dir(self.ca_path, "couchbase", "couchbase", mode=0o700)

            with open(ca_cert, 'r') as f:
                ca_cert_pem = f.read()
            with open(ca_key, 'r') as f:
                ca_key_pem = f.read()

            name_alt = []
            ip_alt = []
            if not self.internal_ip.split('.')[-1].isalpha():
                ip_alt.append(self.internal_ip)
            else:
                name_alt.append(self.internal_ip)

            if self.external_ip:
                if not self.external_ip.split('.')[-1].isalpha():
                    ip_alt.append(self.external_ip)
                else:
                    name_alt.append(self.external_ip)

            logger.info(f"Generating node certificate")

            node_key, node_cert = CertMgr.certificate_standard(ca_cert_pem, ca_key_pem, "Couchbase Server", alt_name=name_alt, alt_ip_list=ip_alt)

            node_cert_file = os.path.join(os.path.dirname(self.ca_path), "chain.pem")
            node_key_file = os.path.join(os.path.dirname(self.ca_path), "pkey.key")

            FileManager().write_file(node_key, node_key_file, "couchbase", "couchbase", mode=0o700)
            FileManager().write_file(node_cert, node_cert_file, "couchbase", "couchbase", mode=0o700)

            api = APISession(self.username, self.password)
            api.set_host(self.internal_ip, 0, 8091)

            logger.info(f"Loading node certificate")

            try:
                api.api_empty_post("/node/controller/reloadCertificate")
            except Exception as err:
                logger.error(f"Failed to load node cert: {err}")
                raise ClusterSetupError(f"Node cert load failed: {err}")

        return True

    def cluster_ca_get(self):
        api = APISession(self.username, self.password)
        api.set_host(self.internal_ip, 0, 8091)
        response = api.api_get("/pools/default/trustedCAs")
        result = response.json()

        if not isinstance(result, list):
            raise ClusterSetupError(f"CA fetch invalid response: response: {result}")

        if len(result) < 2:
            raise ClusterSetupError(f"CA fetch invalid number of certificates (expecting 2, got {len(result)}): response: {result}")

        certificate = result[1].get("pem")

        return certificate

    def cert_wait(self, op_retry=15, factor=0.5):
        home_dir = FileManager().get_user_home()
        ca_key = os.path.join(home_dir, "ca.key")
        ca_cert = os.path.join(home_dir, "ca.pem")
        if os.path.exists(ca_key) and os.path.exists(ca_cert):
            for retry_number in range(op_retry):
                try:
                    self.cluster_ca_get()
                except Exception as err:
                    n_retry = retry_number + 1
                    if n_retry == op_retry:
                        raise ClusterSetupError(f"Cert check failed on {self.internal_ip}: {err}")
                    logger.info(f"Retrying cert check on {self.internal_ip}")
                    wait = factor
                    wait *= n_retry
                    time.sleep(wait)

    def cluster_ca_setup(self):
        if self.internal_ip != NetworkInfo().ip_lookup(self.rally_ip_address):
            logger.info("ca setup: skipping node")
            return True

        if self.community_edition:
            logger.info("ca setup: skipping ca setup on Community Edition")
            print("Skipped: ca setup")
            return True

        self.cluster_ca_load()
        self.cert_wait()

    def node_cert_setup(self):
        if self.community_edition:
            logger.info("rebalance: skipping cert setup on Community Edition")
            print("Skipped: node cert setup")
            return True

        self.host_cert_load()

    def node_init(self):
        if self.is_node():
            return True

        cmd = [
            "/opt/couchbase/bin/couchbase-cli", "node-init",
            "--cluster", self.internal_ip,
            "--username", self.username,
            "--password", self.password,
            "--node-init-hostname", self.internal_ip,
            "--node-init-data-path", self.data_path,
            "--node-init-index-path", self.data_path,
            "--node-init-analytics-path", self.data_path,
            "--node-init-eventing-path", self.data_path,
        ]

        logger.info(f"Initializing node {self.internal_ip}")

        try:
            RunShellCommand().cmd_output(cmd, "/var/tmp")
        except RCNotZero as err:
            raise ClusterSetupError(f"Node init failed: {err}")

        self.node_external_ip()

        return True

    def cluster_init(self):
        self.node_init()
        services = ','.join(self.services)

        if self.community_edition:
            cmd = [
                "/opt/couchbase/bin/couchbase-cli", "cluster-init",
                "--cluster", self.rally_ip_address,
                "--cluster-username", self.username,
                "--cluster-password", self.password,
                "--cluster-port", "8091",
                "--cluster-ramsize", self.data_quota,
                "--cluster-fts-ramsize", self.fts_quota,
                "--cluster-index-ramsize", self.index_quota,
                "--cluster-name", self.cluster_name,
                "--index-storage-setting", self.index_mem_opt.name,
                "--services", services
            ]
        else:
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
                "--services", services
            ]

        logger.info(f"Creating cluster on node {self.internal_ip}")
        edition = "Community" if self.community_edition else "Enterprise"
        logger.info(f"Server Edition: {edition}")

        try:
            RunShellCommand().cmd_output(cmd, "/var/tmp")
        except RCNotZero as err:
            raise ClusterSetupError(f"Cluster init failed: {err}")

        self.node_change_group()

        try:
            self.config_data.set('cluster', 'services', services)
        except configparser.NoSectionError:
            self.config_data['cluster'] = dict(services=services)

        return True

    def node_add(self):
        self.node_init()
        services = ','.join(self.services)

        cmd = [
            "/opt/couchbase/bin/couchbase-cli", "server-add",
            "--cluster", self.rally_ip_address,
            "--username", self.username,
            "--password", self.password,
            "--server-add-username", self.username,
            "--server-add-password", self.password,
            "--server-add", self.internal_ip,
            "--services", services
        ]

        logger.info(f"Adding node {self.internal_ip} to cluster at {self.rally_ip_address}")

        try:
            RunShellCommand().cmd_output(cmd, "/var/tmp")
        except RCNotZero as err:
            raise ClusterSetupError(f"Node add failed: {err}")

        self.node_change_group()

        try:
            self.config_data.set('cluster', 'services', services)
        except configparser.NoSectionError:
            self.config_data['cluster'] = dict(services=services)

        return True

    def node_external_ip(self):
        if not self.external_access:
            return True

        cmd = [
            "/opt/couchbase/bin/couchbase-cli", "setting-alternate-address",
            "--cluster", self.internal_ip,
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

    def node_change_group(self, retry_count=10, factor=0.5):
        if self.community_edition:
            logger.info("Skipping node server group assignment on Community Edition")
            return True
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

        for retry_number in range(retry_count + 1):
            try:
                RunShellCommand().cmd_output(cmd, "/var/tmp")
                return True
            except RCNotZero as err:
                if retry_number == retry_count:
                    raise ClusterSetupError(f"Can not change node group: {err}")
                logger.debug(f"retrying node change group")
                wait = factor
                wait *= (retry_number + 1)
                time.sleep(wait)

    def rebalance(self, retry_count=10, factor=0.5):
        if self.internal_ip != NetworkInfo().ip_lookup(self.rally_ip_address):
            logger.info("rebalance: skipping node")
            return True

        if self.community_edition:
            logger.info("rebalance: skipping rebalance on Community Edition")
            print("Skipped: Rebalance")
            return True

        if not self.cluster_wait(min_nodes=len(self.ip_list)):
            raise ClusterSetupError("rebalance: not all nodes joined the cluster")

        cmd = [
            "/opt/couchbase/bin/couchbase-cli", "rebalance",
            "--cluster", self.rally_ip_address,
            "--username", self.username,
            "--password", self.password,
            "--no-progress-bar"
        ]

        for retry_number in range(retry_count + 1):
            try:
                RunShellCommand().cmd_output(cmd, "/var/tmp")
                print("Success: Rebalance")
                return True
            except RCNotZero as err:
                if retry_number == retry_count:
                    raise ClusterSetupError(f"Can not rebalance cluster: {err}")
                logger.debug(f"retrying cluster rebalance")
                wait = factor
                wait *= (retry_number + 1)
                time.sleep(wait)

    def cluster_wait(self, retry_count=30, factor=0.5, min_nodes=1):
        for retry_number in range(retry_count + 1):
            cmd = [
                "/opt/couchbase/bin/couchbase-cli", "server-list",
                "--cluster", self.rally_ip_address,
                "--username", self.username,
                "--password", self.password,
            ]
            result = RunShellCommand().cmd_output(cmd, "/var/tmp", no_raise=True)
            if result is not None and len(result) >= min_nodes:
                return result
            else:
                if retry_number == retry_count:
                    return False
                logger.info(f"Waiting for cluster to initialize")
                wait = factor
                wait *= (retry_number + 1)
                time.sleep(wait)

    def bootstrap(self):
        logger.info(f"Data path      : {self.data_path}")
        logger.info(f"Services       : {','.join(self.services)}")
        logger.info(f"Data quota     : {self.data_quota}")
        logger.info(f"Analytics quota: {self.analytics_quota}")
        logger.info(f"Index quota    : {self.index_quota}")
        logger.info(f"FTS quota      : {self.fts_quota}")
        logger.info(f"Eventing quota : {self.eventing_quota}")

        if self.internal_ip == self.rally_ip_address and not self.is_cluster():
            logger.info(f"Creating rally node {self.rally_ip_address}")
            self.cluster_init()
            print("Success: Cluster Initialized")
        elif not self.is_node():
            if not self.cluster_wait():
                raise ClusterSetupError(f"can not add node {self.internal_ip} rally node is unreachable")
            logger.info(f"Creating cluster node {self.internal_ip}")
            self.node_add()
            print("Success: Node Added")
        else:
            print("Node is already configured")

    @staticmethod
    def wait_port(address: str, port: int = 8091, retry_count=30, factor=0.5):
        for retry_number in range(retry_count + 1):
            socket.setdefaulttimeout(1)
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            result = sock.connect_ex((address, port))
            sock.close()
            if result == 0:
                return True
            else:
                if retry_number == retry_count:
                    return False
                logger.info(f"Waiting for {address}:{port} to become reachable")
                wait = factor
                wait *= (retry_number + 1)
                time.sleep(wait)
