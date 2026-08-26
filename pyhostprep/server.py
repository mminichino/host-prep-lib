##
##

import os
import re
import psutil
import logging
import socket
import time
import json
from pathlib import Path
from typing import Optional, Sequence, List
from pyhostprep.httpsessionmgr import APISession
from pyhostprep.network import NetworkInfo
from pyhostprep.command import RunShellCommand, RCNotZero
from pyhostprep.exception import FatalError
from pyhostprep.util import FileManager
from pyhostprep.osfamily import OSFamily
from pyhostprep.osinfo import OSRelease
from pyhostprep.certificates import CertMgr
from pyhostprep.models.server_config import IndexMemoryOption, ServerConfig

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


class CouchbaseServer(object):

    def __init__(self, config: ServerConfig):
        self.cluster_name: str = config.name
        self.rally_ip_address: str = config.rally_ip_address if config.rally_ip_address else config.ip_address
        self.ip_address: str = config.ip_address
        self.external_ip_address: Optional[str] = config.external_ip_address
        self.services: Sequence[str] = config.services
        self.username: str = config.username
        self.password: str = config.password
        self.data_path: str = config.data_path
        self.index_mem_opt: IndexMemoryOption = config.index_mem_opt
        self.server_group: str = config.server_group
        self.community_edition: bool = config.community_edition
        self.private_key: Optional[str] = config.private_key
        self.options: List[str] = config.options

        if OSRelease().family == OSFamily.LINUX:
            self.ca_path = r"/opt/couchbase/var/lib/couchbase/inbox/CA"
        elif OSRelease().family == OSFamily.WINDOWS:
            self.ca_path = r"C:\Program Files\couchbase\server\var\lib\couchbase\inbox\CA"
        elif OSRelease().family == OSFamily.MACOS:
            self.ca_path = r"/Applications/Couchbase Server.app/Contents/Resources/couchbase-core/var/lib/couchbase/inbox/CA"
        else:
            raise ClusterSetupError(f"Unknown OS type")

        self.data_quota = None
        self.analytics_quota = None
        self.index_quota = None
        self.fts_quota = None
        self.eventing_quota = None

        self.get_mem_config()

        logger.info(f"Internal IP: {self.ip_address}")
        logger.info(f"External IP: {self.external_ip_address}")
        logger.info(f"Rally Host: {self.rally_ip_address}")
        logger.info(f"Services: {','.join(self.services)}")

        self.admin_port = 8091
        if not self.wait_port(self.ip_address, self.admin_port):
            logger.error(f"Can not connect to admin port on this host ({self.ip_address})")
            raise ClusterSetupError(f"Host {self.ip_address}:{self.admin_port} is not reachable")
        if self.rally_ip_address and not self.wait_port(self.rally_ip_address, self.admin_port):
            logger.error(f"Can not connect to admin port on rally node {self.rally_ip_address}")
            raise ClusterSetupError(f"Host {self.rally_ip_address}:{self.admin_port} is not reachable")

    def get_mem_config(self):
        host_mem = psutil.virtual_memory()
        total_mem = int(host_mem.total / (1024 * 1024))

        os_pool = int(total_mem * 0.3)
        reservation = 2048 if os_pool < 2048 else 4096 if os_pool > 4096 else os_pool

        memory_pool = total_mem - reservation

        service_count = len(self.services)
        if "query" in self.services and len(self.services) > 1:
            service_count -= 1

        if "eventing" in self.services:
            _eventing_mem = int(memory_pool / service_count)
        else:
            _eventing_mem = 256

        if "fts" in self.services:
            _fts_mem = int(memory_pool / service_count)
        else:
            _fts_mem = 256

        if "index" in self.services:
            _index_mem = int(memory_pool / service_count)
        else:
            _index_mem = 256

        if "analytics" in self.services:
            _analytics_mem = int(memory_pool / service_count)
        else:
            _analytics_mem = 1024

        if "data" in self.services:
            _data_mem = int(memory_pool / service_count)
        else:
            _data_mem = 256
                
        self.eventing_quota = str(_eventing_mem)
        self.fts_quota = str(_fts_mem)
        self.index_quota = str(_index_mem)
        self.analytics_quota = str(_analytics_mem)
        self.data_quota = str(_data_mem)

    def is_node(self):
        cmd: list[str] = [
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
            if item[0] == self.ip_address:
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
            api.set_host(self.ip_address, 0, 8091)

            logger.info(f"Loading cluster certificate authority")

            response = api.api_empty_post("/node/controller/loadTrustedCAs")
            result = response.json()

            if not isinstance(result, list) or result[0].get("id") != 1:
                logger.error(f"Failed to load CA: response: {response.json()}")
                raise ClusterSetupError(f"CA load failed")

        return True

    @staticmethod
    def _address_alt_names(address: str, name_alt: List[str], ip_alt: List[str]) -> None:
        if not address.split('.')[-1].isalpha():
            ip_alt.append(address)
        else:
            name_alt.append(address)

    def _cert_alt_names(self, external_ip_address: Optional[str] = None) -> tuple[List[str], List[str]]:
        name_alt: List[str] = []
        ip_alt: List[str] = []
        self._address_alt_names(self.ip_address, name_alt, ip_alt)
        external_ip = external_ip_address if external_ip_address is not None else self.external_ip_address
        if external_ip:
            self._address_alt_names(external_ip, name_alt, ip_alt)
        return name_alt, ip_alt

    def _ca_candidate_dirs(self) -> List[str]:
        dirs = [
            os.path.dirname(self.ca_path),
            FileManager().get_user_home(),
            str(Path.home()),
            self.data_path,
        ]
        # Preserve order while removing duplicates
        seen = set()
        unique: List[str] = []
        for path in dirs:
            if path and path not in seen:
                seen.add(path)
                unique.append(path)
        return unique

    def _ca_key_path(self) -> Optional[str]:
        for directory in self._ca_candidate_dirs():
            candidate = os.path.join(directory, "ca.key")
            if os.path.exists(candidate):
                return candidate
        return None

    def _ca_cert_path(self) -> Optional[str]:
        for directory in self._ca_candidate_dirs():
            for name in ("ca.pem", "ca.crt"):
                candidate = os.path.join(directory, name)
                if os.path.exists(candidate):
                    return candidate
        return None

    def _write_and_reload_node_cert(self, node_key: str, node_cert: str) -> None:
        FileManager().make_dir(self.ca_path, "couchbase", "couchbase", mode=0o700)
        node_cert_file = os.path.join(os.path.dirname(self.ca_path), "chain.pem")
        node_key_file = os.path.join(os.path.dirname(self.ca_path), "pkey.key")

        FileManager().write_file(node_key, node_key_file, "couchbase", "couchbase", mode=0o700)
        FileManager().write_file(node_cert, node_cert_file, "couchbase", "couchbase", mode=0o700)

        api = APISession(self.username, self.password)
        api.set_host(self.ip_address, 0, 8091)

        logger.info(f"Loading node certificate")

        try:
            api.api_empty_post("/node/controller/reloadCertificate")
        except Exception as err:
            logger.error(f"Failed to load node cert: {err}")
            raise ClusterSetupError(f"Node cert load failed: {err}")

    def host_cert_load(self):
        home_dir = FileManager().get_user_home()
        ca_key = os.path.join(home_dir, "ca.key")
        ca_cert = os.path.join(home_dir, "ca.pem")
        if os.path.exists(ca_key) and os.path.exists(ca_cert):
            with open(ca_cert, 'r') as f:
                ca_cert_pem = f.read()
            with open(ca_key, 'r') as f:
                ca_key_pem = f.read()

            name_alt, ip_alt = self._cert_alt_names()

            logger.info(f"Generating node certificate")

            node_key, node_cert = CertMgr.certificate_standard(
                ca_cert_pem, ca_key_pem, "Couchbase Server", alt_name=name_alt, alt_ip_list=ip_alt
            )
            self._write_and_reload_node_cert(node_key, node_cert)

        return True

    def trusted_cas_list(self) -> list:
        api = APISession(self.username, self.password)
        api.set_host(self.ip_address, 0, 8091)
        response = api.api_get("/pools/default/trustedCAs")
        result = response.json()

        if not isinstance(result, list) or not result:
            raise ClusterSetupError(f"CA fetch invalid response: response: {result}")

        return result

    def trusted_root_ca_get(self, ca_key_pem: Optional[str] = None) -> str:
        result = self.trusted_cas_list()

        if ca_key_pem:
            for entry in result:
                certificate = entry.get("pem")
                if certificate and CertMgr.key_matches_cert(ca_key_pem, certificate):
                    return certificate
            raise ClusterSetupError("No trusted CA matches the local CA private key")

        if len(result) >= 2:
            certificate = result[1].get("pem")
        else:
            certificate = result[0].get("pem")

        if not certificate:
            raise ClusterSetupError(f"CA fetch missing certificate PEM: response: {result}")

        return certificate

    def _bootstrap_ca(self) -> None:
        home_dir = FileManager().get_user_home()
        ca_key = os.path.join(home_dir, "ca.key")
        ca_cert = os.path.join(home_dir, "ca.pem")

        if not (os.path.exists(ca_key) and os.path.exists(ca_cert)):
            logger.info("Generating cluster certificate authority")
            key_bytes, cert_bytes = CertMgr().certificate_ca()
            with open(ca_key, 'w') as f:
                f.write(key_bytes.decode('utf-8'))
            with open(ca_cert, 'w') as f:
                f.write(cert_bytes.decode('utf-8'))
            os.chmod(ca_key, 0o600)
            os.chmod(ca_cert, 0o600)

        self.cluster_ca_load()

    def _ensure_home_ca(self, ca_key_pem: str, ca_cert_pem: str) -> None:
        home_dir = FileManager().get_user_home()
        ca_key = os.path.join(home_dir, "ca.key")
        ca_cert = os.path.join(home_dir, "ca.pem")
        with open(ca_key, 'w') as f:
            f.write(ca_key_pem)
        with open(ca_cert, 'w') as f:
            f.write(ca_cert_pem)
        os.chmod(ca_key, 0o600)
        os.chmod(ca_cert, 0o600)

    def _resolve_ca_materials(self) -> tuple[str, str]:
        ca_key_path = self._ca_key_path()
        ca_cert_path = self._ca_cert_path()

        if ca_key_path:
            with open(ca_key_path, 'r') as f:
                ca_key_pem = f.read()

            if ca_cert_path:
                with open(ca_cert_path, 'r') as f:
                    ca_cert_pem = f.read()
                if CertMgr.key_matches_cert(ca_key_pem, ca_cert_pem):
                    try:
                        return self.trusted_root_ca_get(ca_key_pem), ca_key_pem
                    except ClusterSetupError:
                        logger.info("Local CA not yet trusted by cluster; loading CA")
                        self._ensure_home_ca(ca_key_pem, ca_cert_pem)
                        self.cluster_ca_load()
                        return self.trusted_root_ca_get(ca_key_pem), ca_key_pem

            try:
                return self.trusted_root_ca_get(ca_key_pem), ca_key_pem
            except ClusterSetupError:
                logger.info("Local CA key does not match cluster trusted CAs; creating new CA")

        self._bootstrap_ca()
        home_ca_key = os.path.join(FileManager().get_user_home(), "ca.key")
        if not os.path.exists(home_ca_key):
            raise ClusterSetupError("CA private key not found after bootstrap")

        with open(home_ca_key, 'r') as f:
            ca_key_pem = f.read()
        return self.trusted_root_ca_get(ca_key_pem), ca_key_pem

    def fetch_node_external_ip(self) -> Optional[str]:
        api = APISession(self.username, self.password)
        api.set_host(self.ip_address, 0, 8091)
        response = api.api_get("/pools/default")
        for node in response.json().get("nodes", []):
            hostname = node.get("hostname", "").split(":")[0]
            if hostname != self.ip_address:
                continue
            alternate_addresses = node.get("alternateAddresses", {})
            external = alternate_addresses.get("external", {})
            external_hostname = external.get("hostname")
            if external_hostname:
                return external_hostname.split(":")[0]
        return None

    def host_cert_update(self, external_ip_address: Optional[str] = None):
        ca_cert_pem, ca_key_pem = self._resolve_ca_materials()

        external_ip = external_ip_address
        if external_ip is None:
            external_ip = self.external_ip_address or self.fetch_node_external_ip()

        name_alt, ip_alt = self._cert_alt_names(external_ip)

        logger.info(f"Generating node certificate")

        node_key, node_cert = CertMgr.certificate_standard(
            ca_cert_pem, ca_key_pem, "Couchbase Server", alt_name=name_alt, alt_ip_list=ip_alt
        )
        self._write_and_reload_node_cert(node_key, node_cert)
        return True

    def node_cert_update(self):
        if self.community_edition:
            logger.info("cert update: skipping cert update on Community Edition")
            print("Skipped: node cert update")
            return True

        self.host_cert_update()
        print("Success: Node certificate updated")
        return True

    def cluster_ca_get(self):
        api = APISession(self.username, self.password)
        api.set_host(self.ip_address, 0, 8091)
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
                    return True
                except Exception as err:
                    n_retry = retry_number + 1
                    if n_retry == op_retry:
                        raise ClusterSetupError(f"Cert check failed on {self.ip_address}: {err}")
                    logger.info(f"Retrying cert check on {self.ip_address}")
                    wait = factor
                    wait *= n_retry
                    time.sleep(wait)
        return False

    def cluster_ca_setup(self):
        if self.ip_address != NetworkInfo().ip_lookup(self.rally_ip_address):
            logger.info("ca setup: skipping node")
            return True

        if self.community_edition:
            logger.info("ca setup: skipping ca setup on Community Edition")
            print("Skipped: ca setup")
            return True

        self.cluster_ca_load()
        return self.cert_wait()

    def node_cert_setup(self):
        if self.community_edition:
            logger.info("rebalance: skipping cert setup on Community Edition")
            print("Skipped: node cert setup")
            return True

        return self.host_cert_load()

    def cluster_cert_auth_setup(self):
        if self.ip_address != NetworkInfo().ip_lookup(self.rally_ip_address):
            logger.info("cert auth: skipping node")
            return True

        if self.community_edition:
            logger.info("cert auth: skipping rebalance on Community Edition")
            print("Skipped: cert auth setup")
            return True

        parameters = {
            "state": "enable",
            "prefixes": [
                {
                    "path": "subject.cn",
                    "prefix": "",
                    "delimiter": "."
                },
                {
                    "path": "san.email",
                    "prefix": "",
                    "delimiter": "@"
                }
            ]
        }

        with open('/var/tmp/mtls.json', 'w') as f:
            json.dump(parameters, f)

        cmd = [
            "/opt/couchbase/bin/couchbase-cli", "ssl-manage",
            "--cluster", self.rally_ip_address,
            "--username", self.username,
            "--password", self.password,
            "--set-client-auth", "/var/tmp/mtls.json"
        ]

        try:
            RunShellCommand().cmd_output(cmd, "/var/tmp")
        except RCNotZero as err:
            raise ClusterSetupError(f"cert auth setup failed: {err}")

        return True

    def node_init(self):
        if self.is_node():
            return True

        cmd = [
            "/opt/couchbase/bin/couchbase-cli", "node-init",
            "--cluster", self.ip_address,
            "--username", self.username,
            "--password", self.password,
            "--node-init-hostname", self.ip_address,
            "--node-init-data-path", self.data_path,
            "--node-init-index-path", self.data_path,
            "--node-init-analytics-path", self.data_path,
            "--node-init-eventing-path", self.data_path,
        ]

        logger.info(f"Initializing node {self.ip_address}")

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

        logger.info(f"Creating cluster on node {self.rally_ip_address}")
        edition = "Community" if self.community_edition else "Enterprise"
        logger.info(f"Server Edition: {edition}")

        try:
            RunShellCommand().cmd_output(cmd, "/var/tmp")
        except RCNotZero as err:
            raise ClusterSetupError(f"Cluster init failed: {err}")

        self.node_change_group()

        return True

    def node_add(self):
        self.node_init()
        self.cluster_update()
        services = ','.join(self.services)

        cmd = [
            "/opt/couchbase/bin/couchbase-cli", "server-add",
            "--cluster", self.rally_ip_address,
            "--username", self.username,
            "--password", self.password,
            "--server-add-username", self.username,
            "--server-add-password", self.password,
            "--server-add", self.ip_address,
            "--services", services
        ]

        logger.info(f"Adding node {self.ip_address} to cluster at {self.rally_ip_address}")

        try:
            RunShellCommand().cmd_output(cmd, "/var/tmp")
        except RCNotZero as err:
            raise ClusterSetupError(f"Node add failed: {err}")

        self.node_change_group()

        return True

    def cluster_update(self):
        if "data" in self.services:
            return

        cmd = [
            "/opt/couchbase/bin/couchbase-cli", "setting-cluster",
            "--cluster", self.rally_ip_address,
            "--username", self.username,
            "--password", self.password,
        ]

        if "fts" in self.services:
            cmd += [
                "--cluster-fts-ramsize", self.fts_quota,
            ]

        if "index" in self.services:
            cmd += [
                "--cluster-index-ramsize", self.index_quota,
            ]

        if "eventing" in self.services:
            cmd += [
                "--cluster-eventing-ramsize", self.eventing_quota,
            ]

        if "analytics" in self.services:
            cmd += [
                "--cluster-analytics-ramsize", self.analytics_quota,
            ]

        logger.info(f"Updating cluster settings on node {self.rally_ip_address}")

        try:
            RunShellCommand().cmd_output(cmd, "/var/tmp")
        except RCNotZero as err:
            raise ClusterSetupError(f"Cluster update failed: {err}")

        return

    def node_external_ip(self):
        if not self.external_ip_address:
            return True

        cmd = [
            "/opt/couchbase/bin/couchbase-cli", "setting-alternate-address",
            "--cluster", self.ip_address,
            "--username", self.username,
            "--password", self.password,
            "--set",
            "--node", self.ip_address,
            "--hostname", self.external_ip_address,
        ]

        try:
            RunShellCommand().cmd_output(cmd, "/var/tmp")
        except RCNotZero as err:
            raise ClusterSetupError(f"External address config failed: {err}")

        return True

    def update_external_ip(self):
        if not self.external_ip_address:
            raise ClusterSetupError("External IP address is required")

        logger.info(f"Updating external IP address to {self.external_ip_address}")
        self.node_external_ip()
        print("Success: External IP updated")
        return True

    def _node_cert_for_external_ip(self):
        if not self.external_ip_address or self.community_edition:
            return True

        if self._ca_key_path():
            logger.info("Updating node certificate with external IP alternate name")
            return self.host_cert_update()

        return self.host_cert_load()

    def is_group(self):
        cmd = [
            "/opt/couchbase/bin/couchbase-cli", "group-manage",
            "--cluster", self.rally_ip_address,
            "--username", self.username,
            "--password", self.password,
            "--list",
            "--group-name", self.server_group
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
            "--group-name", self.server_group
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
                if node_ip == self.ip_address:
                    return name

        return None

    def node_change_group(self, retry_count=10, factor=0.5):
        if self.community_edition:
            logger.info("Skipping node server group assignment on Community Edition")
            return True
        current_group = self.get_node_group()
        if current_group == self.server_group:
            return True

        if not self.is_group():
            self.create_group()

        cmd = [
            "/opt/couchbase/bin/couchbase-cli", "group-manage",
            "--cluster", self.rally_ip_address,
            "--username", self.username,
            "--password", self.password,
            "--move-servers", self.ip_address,
            "--from-group", current_group,
            "--to-group", self.server_group
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
        return False

    def rebalance(self, retry_count=10, factor=0.5):
        if self.community_edition:
            logger.info("rebalance: skipping rebalance on Community Edition")
            print("Skipped: Rebalance")
            return True

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
        return False

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
        return None

    def create_cluster(self):
        logger.info(f"Data path      : {self.data_path}")
        logger.info(f"Services       : {','.join(self.services)}")
        logger.info(f"Data quota     : {self.data_quota}")
        logger.info(f"Analytics quota: {self.analytics_quota}")
        logger.info(f"Index quota    : {self.index_quota}")
        logger.info(f"FTS quota      : {self.fts_quota}")
        logger.info(f"Eventing quota : {self.eventing_quota}")

        if not self.is_cluster():
            logger.info(f"Creating cluster with node {self.rally_ip_address}")
            self.cluster_init()
            self._node_cert_for_external_ip()
            print("Success: Cluster Initialized")
        else:
            print("Cluster is already configured")

    def add_node(self):
        logger.info(f"Data path: {self.data_path}")
        logger.info(f"Services : {','.join(self.services)}")

        if not self.is_node():
            if not self.cluster_wait():
                raise ClusterSetupError(f"can not add node {self.rally_ip_address} rally node is unreachable")
            logger.info(f"Adding cluster node {self.ip_address}")
            self.node_add()
            self._node_cert_for_external_ip()
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
        return None
