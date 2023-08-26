##
##

import logging
import warnings
from overrides import override
from pyhostprep.cli import CLI

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
        cluster_parser = cluster.add_subparsers(dest='action')
        cluster_parser.required = True
        config_parser = cluster_parser.add_parser('download')
        config_parser.add_argument('-n', '--name', dest='name', action='store')

    def run(self):
        print(self.options.command)


def main(args=None):
    cli = SWMgrCLI(args)
    cli.run()
