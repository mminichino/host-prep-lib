##
##

import logging
import warnings
import argparse
from overrides import override
from pyhostprep.cli import CLI
from pyhostprep.server import CouchbaseServer, IndexMemoryOption
from pyhostprep.server import ServerConfig

warnings.filterwarnings("ignore")
logger = logging.getLogger()


class SWMgrCLI(CLI):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @override()
    def local_args(self):
        opt_parser = argparse.ArgumentParser(parents=[self.parser], add_help=False)
        opt_parser.add_argument('-n', '--name', dest='name', action='store', default='cbdb')
        opt_parser.add_argument('-l', '--ip_list', dest='ip_list', action='store')
        opt_parser.add_argument('-s', '--services', dest='services', action='store', default='data,index,query')
        opt_parser.add_argument('-u', '--username', dest='username', action='store', default='Administrator')
        opt_parser.add_argument('-p', '--password', dest='password', action='store', default='password')
        opt_parser.add_argument('-i', '--index_mem', dest='index_mem', action='store', default='default')
        opt_parser.add_argument('-g', '--group', dest='group', action='store', default='primary')
        opt_parser.add_argument('-D', '--data_path', dest='data_path', action='store', default='/opt/couchbase/var/lib/couchbase/data')

        command_subparser = self.parser.add_subparsers(dest='command')
        cluster_parser = command_subparser.add_parser('cluster', parents=[opt_parser], add_help=False)
        action_subparser = cluster_parser.add_subparsers(dest='cluster_command')
        action_subparser.add_parser('create', parents=[opt_parser], add_help=False)
        action_subparser.add_parser('rebalance', parents=[opt_parser], add_help=False)

    def cluster_operations(self):
        sc = ServerConfig(self.options.name,
                          self.options.ip_list.split(','),
                          self.options.services.split(','),
                          self.options.username,
                          self.options.password,
                          IndexMemoryOption[self.options.index_mem],
                          self.options.group,
                          self.options.data_path)
        cbs = CouchbaseServer(sc)
        if self.options.cluster_command == "create":
            cbs.bootstrap()
        elif self.options.cluster_command == "rebalance":
            cbs.rebalance()

    def run(self):
        if self.options.command == "cluster":
            self.cluster_operations()


def main(args=None):
    cli = SWMgrCLI(args)
    cli.run()
