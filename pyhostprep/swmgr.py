##
##

import logging
import warnings
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
        command_parser = self.parser.add_subparsers(dest='command')
        command_parser.required = True
        cluster = command_parser.add_parser('cluster')
        cluster.add_argument('-n', '--name', dest='name', action='store')
        cluster.add_argument('-l', '--ip_list', dest='ip_list', action='store')
        cluster.add_argument('-s', '--services', dest='services', action='store', default='data,index,query')
        cluster.add_argument('-u', '--username', dest='username', action='store', default='Administrator')
        cluster.add_argument('-p', '--password', dest='password', action='store', default='password')
        cluster.add_argument('-i', '--index_mem', dest='index_mem', action='store', default='default')
        cluster.add_argument('-g', '--group', dest='group', action='store', default='primary')
        cluster.add_argument('-d', '--data_path', dest='data_path', action='store', default='/opt/couchbase/var/lib/couchbase/data')

    def cluster_bootstrap(self):
        sc = ServerConfig(self.options.name,
                          self.options.ip_list.split(','),
                          self.options.services.split(','),
                          self.options.username,
                          self.options.password,
                          IndexMemoryOption[self.options.index_mem],
                          self.options.group,
                          self.options.data_path)
        cbs = CouchbaseServer(sc)
        cbs.bootstrap()

    def run(self):
        if self.options.command == "cluster":
            self.cluster_bootstrap()


def main(args=None):
    cli = SWMgrCLI(args)
    cli.run()
