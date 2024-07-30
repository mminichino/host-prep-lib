##
##

import logging
import os
import warnings
import argparse
import sys
from overrides import override
from pyhostprep.cli import CLI
from pyhostprep.server import CouchbaseServer, IndexMemoryOption
from pyhostprep.server import ServerConfig
from pyhostprep.gateway import GatewayConfig, SyncGateway
from pyhostprep.certificates import CertMgr

warnings.filterwarnings("ignore")
logger = logging.getLogger()


class SWMgrCLI(CLI):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @override()
    def local_args(self):
        opt_parser = argparse.ArgumentParser(parents=[self.parser], add_help=False)
        opt_parser.add_argument('-n', '--name', dest='name', action='store', default='cbdb')
        opt_parser.add_argument('-l', '--ip_list', dest='ip_list', action='store', default='127.0.0.1')
        opt_parser.add_argument('-s', '--services', dest='services', action='store', default='data,index,query')
        opt_parser.add_argument('-u', '--username', dest='username', action='store', default='Administrator')
        opt_parser.add_argument('-p', '--password', dest='password', action='store', default='password')
        opt_parser.add_argument('-h', '--host_list', dest='host_list', action='store', default='null')
        opt_parser.add_argument('-L', '--service_list', dest='service_list', action='store', default='null')
        opt_parser.add_argument('-b', '--bucket', dest='bucket', action='store', default='default')
        opt_parser.add_argument('-i', '--index_mem', dest='index_mem', action='store', default='default')
        opt_parser.add_argument('-g', '--group', dest='group', action='store', default='primary')
        opt_parser.add_argument('-D', '--data_path', dest='data_path', action='store', default='/opt/couchbase/var/lib/couchbase/data')
        opt_parser.add_argument('-S', '--sgw_path', dest='sgw_path', action='store', default='/home/sync_gateway')
        opt_parser.add_argument('-f', '--filename', dest='filename', action='store')
        opt_parser.add_argument('-C', '--community', dest='community', action='store_true')
        opt_parser.add_argument('-d', '--domain', dest='domain_name', action='store')
        opt_parser.add_argument('-A', '--alt_names', dest='alt_names',  nargs='+', action='append')
        opt_parser.add_argument('-H', '--host_cert', dest='host_cert', action='store_true')
        opt_parser.add_argument('-k', '--key_file', dest='key_file', action='store')
        opt_parser.add_argument('-c', '--cert_file', dest='cert_file', action='store')
        opt_parser.add_argument('-K', '--private_key', dest='private_key', action='store')
        opt_parser.add_argument('-T', '--tls', dest='tls', action='store_true')
        opt_parser.add_argument('--base64', dest='base64', action='store_true')

        command_subparser = self.parser.add_subparsers(dest='command')
        cluster_parser = command_subparser.add_parser('cluster', parents=[opt_parser], add_help=False)
        action_subparser = cluster_parser.add_subparsers(dest='cluster_command')
        action_subparser.add_parser('create', parents=[opt_parser], add_help=False)
        action_subparser.add_parser('rebalance', parents=[opt_parser], add_help=False)
        action_subparser.add_parser('ca_cert', parents=[opt_parser], add_help=False)
        action_subparser.add_parser('node_cert', parents=[opt_parser], add_help=False)
        action_subparser.add_parser('cert_auth', parents=[opt_parser], add_help=False)
        action_subparser.add_parser('wait', parents=[opt_parser], add_help=False)
        gateway_parser = command_subparser.add_parser('gateway', parents=[opt_parser], add_help=False)
        gateway_subparser = gateway_parser.add_subparsers(dest='gateway_command')
        gateway_subparser.add_parser('configure', parents=[opt_parser], add_help=False)
        gateway_subparser.add_parser('wait', parents=[opt_parser], add_help=False)
        cert_parser = command_subparser.add_parser('cert', parents=[opt_parser], add_help=False)
        cert_subparser = cert_parser.add_subparsers(dest='cert_command')
        cert_subparser.add_parser('key', parents=[opt_parser], add_help=False)
        cert_subparser.add_parser('create', parents=[opt_parser], add_help=False)
        cert_subparser.add_parser('user', parents=[opt_parser], add_help=False)
        cert_subparser.add_parser('ca', parents=[opt_parser], add_help=False)

    def cluster_operations(self):
        sc = ServerConfig(self.options.name,
                          self.options.ip_list.split(','),
                          self.options.services.split(','),
                          self.options.username,
                          self.options.password,
                          self.options.host_list.split(',') if self.options.host_list and self.options.host_list != 'null' else [],
                          self.options.service_list.split(':') if self.options.service_list and self.options.service_list != 'null' else [],
                          IndexMemoryOption[self.options.index_mem],
                          self.options.group,
                          self.options.data_path,
                          self.options.community,
                          self.options.private_key if self.options.private_key else 'null')
        cbs = CouchbaseServer(sc)
        if self.options.cluster_command == "create":
            logger.info(f"Creating cluster {self.options.name} node")
            cbs.bootstrap()
        elif self.options.cluster_command == "rebalance":
            logger.info(f"Balancing cluster {self.options.name}")
            cbs.rebalance()
        elif self.options.cluster_command == "ca_cert":
            logger.info(f"CA setup actions on {self.options.name}")
            cbs.cluster_ca_setup()
        elif self.options.cluster_command == "node_cert":
            logger.info(f"Node certificate actions on {self.options.name}")
            cbs.node_cert_setup()
        elif self.options.cluster_command == "cert_auth":
            logger.info(f"Cert auth setup on {self.options.name}")
            cbs.cluster_cert_auth_setup()
        elif self.options.cluster_command == "wait":
            logger.info(f"Waiting for cluster availability {self.options.name}")
            cbs.cluster_wait()

    def gateway_operations(self):
        gc = GatewayConfig(self.options.ip_list.split(','),
                           self.options.username,
                           self.options.password,
                           self.options.bucket,
                           self.options.sgw_path,
                           use_ssl=self.options.tls)
        sgw = SyncGateway(gc)
        if self.options.gateway_command == "configure":
            if not self.options.filename:
                logger.info(f"Configuring Sync Gateway node")
                sgw.configure()
            else:
                sgw.prepare(dest=self.options.filename)
        elif self.options.gateway_command == "wait":
            logger.info(f"Waiting for Sync Gateway node")
            sgw.gateway_wait()

    def certificate_operations(self):
        if self.options.alt_names is not None:
            alt_names = []
            for names in self.options.alt_names:
                alt_names.extend(names)
        else:
            alt_names = None

        if self.options.cert_command == "key":
            filename = self.options.filename if self.options.filename else "privkey.pem"
            CertMgr().private_key(filename)
        elif self.options.cert_command == "create":
            filename = self.options.filename if self.options.filename else "cert.pem"
            key_file = self.options.key_file if self.options.key_file else "privkey.pem"
            if self.options.host_cert:
                CertMgr().certificate_hostname(filename, key_file, self.options.domain_name, alt_names)
            else:
                CertMgr().certificate_basic(filename, key_file)
        elif self.options.cert_command == "user":
            CertMgr().certificate_user(self.options.cert_file, self.options.key_file, self.options.password, self.options.username)
        elif self.options.cert_command == "ca":
            if self.options.base64:
                key_encoded, cert_encoded = CertMgr().certificate_ca_base64()
                print("---- Begin Certificate Key ----")
                print(key_encoded)
                print("---- End Certificate Key ----")
                print("---- Begin Certificate ----")
                print(cert_encoded)
                print("---- End Certificate ----")
            else:
                key_file = os.path.join(self.options.data_path, "ca.key")
                cert_file = os.path.join(self.options.data_path, "ca.crt")
                CertMgr().certificate_ca_files(key_file, cert_file)

    def run(self):
        if self.options.command == "cluster":
            self.cluster_operations()
        elif self.options.command == "gateway":
            self.gateway_operations()
        elif self.options.command == "cert":
            self.certificate_operations()


def main(args=None):
    cli = SWMgrCLI(args)
    cli.run()
    sys.exit(0)
