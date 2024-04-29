##
##

import logging
import warnings
import argparse
import sys
from overrides import override
from pyhostprep.cli import CLI
from pyhostprep.server import CouchbaseServer, IndexMemoryOption
from pyhostprep.server import ServerConfig
from pyhostprep.gateway import GatewayConfig, SyncGateway

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

        command_subparser = self.parser.add_subparsers(dest='command')
        cluster_parser = command_subparser.add_parser('cluster', parents=[opt_parser], add_help=False)
        action_subparser = cluster_parser.add_subparsers(dest='cluster_command')
        action_subparser.add_parser('create', parents=[opt_parser], add_help=False)
        action_subparser.add_parser('rebalance', parents=[opt_parser], add_help=False)
        action_subparser.add_parser('wait', parents=[opt_parser], add_help=False)
        gateway_parser = command_subparser.add_parser('gateway', parents=[opt_parser], add_help=False)
        gateway_subparser = gateway_parser.add_subparsers(dest='gateway_command')
        gateway_subparser.add_parser('configure', parents=[opt_parser], add_help=False)
        gateway_subparser.add_parser('wait', parents=[opt_parser], add_help=False)

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
                          self.options.data_path)
        cbs = CouchbaseServer(sc)
        if self.options.cluster_command == "create":
            logger.info(f"Creating cluster {self.options.name} node")
            cbs.bootstrap()
        elif self.options.cluster_command == "rebalance":
            logger.info(f"Balancing cluster {self.options.name}")
            cbs.rebalance()
        elif self.options.cluster_command == "wait":
            logger.info(f"Waiting for cluster availability {self.options.name}")
            cbs.cluster_wait()

    def gateway_operations(self):
        gc = GatewayConfig(self.options.ip_list.split(','),
                           self.options.username,
                           self.options.password,
                           self.options.bucket,
                           self.options.sgw_path)
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

    def run(self):
        if self.options.command == "cluster":
            self.cluster_operations()
        elif self.options.command == "gateway":
            self.gateway_operations()


def main(args=None):
    cli = SWMgrCLI(args)
    cli.run()
    sys.exit(0)
