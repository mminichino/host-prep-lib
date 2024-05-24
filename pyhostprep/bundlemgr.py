##
##

import logging
import warnings
import sys
import ansible_runner
from overrides import override
from pyhostprep.software import SoftwareManager
from pyhostprep.cli import CLI, StreamOutputLogger
from pyhostprep import get_playbook_file

warnings.filterwarnings("ignore")
logger = logging.getLogger()


class BundleMgrCLI(CLI):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @override()
    def local_args(self):
        self.parser.add_argument('-b', '--bundles', nargs='+', help='List of bundles to deploy')
        self.parser.add_argument('-V', '--version', action='store', help="Software Version", default="latest")
        self.parser.add_argument('-C', '--community', action='store_true', help="Software Edition")

    def is_time_synced(self):
        return self.host_info.system.is_running("ntp") \
            or self.host_info.system.is_running("ntpd") \
            or self.host_info.system.is_running("systemd-timesyncd") \
            or self.host_info.system.is_running("chrony") \
            or self.host_info.system.is_running("chronyd")

    def is_firewalld_enabled(self):
        return self.host_info.system.is_running("firewalld")

    def run(self):
        os_name = self.op.os.os_name
        os_major = self.op.os.os_major_release
        os_minor = self.op.os.os_minor_release
        os_arch = self.op.os.architecture
        logger.info(f"Running on {os_name} version {os_major} {os_arch}")
        extra_vars = {
            'package_root': self.data,
            'os_name': os_name,
            'os_major': os_major,
            'os_minor': os_minor,
            'os_arch': os_arch,
            'time_svc_enabled': self.is_time_synced(),
            'firewalld_enabled': self.is_firewalld_enabled()
        }

        if self.options.community:
            enterprise = False
        else:
            enterprise = True

        for b in self.options.bundles:
            self.op.add(b)

        self.run_timestamp("begins")

        for bundle in self.op.install_list():
            logger.info(f"Executing bundle {bundle.name}")
            for playbook in [bundle.pre, bundle.run, bundle.post]:
                if not playbook:
                    continue
                for extra_var in bundle.extra_vars:
                    logger.info(f"Getting value for variable {extra_var}")
                    if extra_var == "cbs_download_url":
                        sw = SoftwareManager()
                        version = self.options.version if self.options.version and self.options.version != 'latest' else sw.cbs_latest
                        url = sw.get_cbs_download(version, self.op, enterprise)
                        extra_vars.update({'cbs_download_url': url})
                    elif extra_var == "sgw_download_rpm":
                        sw = SoftwareManager()
                        version = self.options.version if self.options.version and self.options.version != 'latest' else sw.sgw_latest(self.op)
                        url = sw.get_sgw_rpm(version, self.op.os.machine, enterprise)
                        extra_vars.update({'sgw_download_rpm': url})
                    elif extra_var == "sgw_download_deb":
                        sw = SoftwareManager()
                        version = self.options.version if self.options.version and self.options.version != 'latest' else sw.sgw_latest(self.op)
                        url = sw.get_sgw_apt(version, self.op.os.machine, enterprise)
                        extra_vars.update({'sgw_download_deb': url})
                    elif extra_var == "libcouchbase_repo":
                        sw = SoftwareManager()
                        repo = sw.get_libcouchbase_repo(os_name, os_major)
                        extra_vars.update({'libcouchbase_repo': repo})
                logger.info(f"Running playbook {playbook}")
                stdout_save = sys.stdout
                sys.stdout = StreamOutputLogger(logger, logging.INFO)
                r = ansible_runner.run(playbook=f"{get_playbook_file(playbook)}", extravars=extra_vars)
                sys.stdout = stdout_save
                logger.info(f"Playbook status: {r.status}")
                if r.rc != 0:
                    logger.error(r.stats)
                    self.run_timestamp("failed")
                    sys.exit(r.rc)

        self.run_timestamp("successful")


def main(args=None):
    cli = BundleMgrCLI(args)
    cli.run()
