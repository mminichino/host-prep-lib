##
##

import requests
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
import re
import json
import warnings
from pyhostprep.bundles import SoftwareBundle
from pyhostprep.retry import retry


class SoftwareManager(object):
    os_aliases = {
        'sles': 'suse',
        'ol': 'oel',
        'opensuse-leap': 'suse'
    }
    os_release_aliases = {
        '20': '20.04'
    }
    pkg_type = {
        'amzn': 'rpm',
        'rhel': 'rpm',
        'centos': 'rpm',
        'ol': 'rpm',
        'rocky': 'rpm',
        'fedora': 'rpm',
        'sles': 'rpm',
        'opensuse-leap': 'rpm',
        'ubuntu': 'deb',
        'debian': 'deb',
    }
    os_version_list = {
        'amzn': ['2023'],
        'rhel': ['8', '9'],
        'centos': ['8'],
        'ol': ['8', '9'],
        'rocky': ['8', '9'],
        'fedora': ['34'],
        'sles': ['12', '15'],
        'opensuse-leap': ['15'],
        'ubuntu': ['20.04', '22'],
        'debian': ['10', '11'],
    }

    def __init__(self):
        warnings.filterwarnings("ignore")

    @property
    def cbs_latest(self):
        releases = self.get_cbs_tags()
        return releases[0]

    @retry()
    def get_cbs_tags(self, name: str = "couchbase"):
        items = []
        session = requests.Session()
        retries = Retry(total=60,
                        backoff_factor=0.1,
                        status_forcelist=[500, 501, 503])
        session.mount('http://', HTTPAdapter(max_retries=retries))
        session.mount('https://', HTTPAdapter(max_retries=retries))

        response = requests.get(f"https://registry.hub.docker.com/v2/repositories/library/{name}/tags", verify=False, timeout=15)

        if response.status_code != 200:
            raise Exception("can not get release tags")

        while True:
            response_json = json.loads(response.text)
            items.extend(response_json.get('results'))
            if response_json.get('next'):
                next_url = response_json.get('next')
                response = requests.get(next_url, verify=False, timeout=15)
            else:
                break

        releases = [r['name'] for r in items if re.match(r"^[0-9]*\.[0-9]*\.[0-9]$", r['name'])]
        major_nums = set([n.split('.')[0] for n in releases])
        current_majors = list(sorted(major_nums))[-2:]
        current_releases = [r for r in sorted(releases, reverse=True) if r.startswith(tuple(current_majors))]

        return current_releases

    @retry()
    def get_cbs_download(self, release: str, op: SoftwareBundle):
        session = requests.Session()
        retries = Retry(total=60,
                        backoff_factor=0.1,
                        status_forcelist=[500, 501, 503])
        session.mount('http://', HTTPAdapter(max_retries=retries))
        session.mount('https://', HTTPAdapter(max_retries=retries))

        arch = op.os.architecture
        os_name = op.os.os_name
        os_release = op.os.os_major_release

        os_name_str = SoftwareManager.os_aliases.get(os_name, os_name)
        os_release_str = SoftwareManager.os_release_aliases.get(os_release, os_release)
        platform = f"{os_name_str}{os_release_str}"
        for test_platform in [platform, 'linux']:
            if SoftwareManager.pkg_type.get(os_name) == "rpm":
                platform_link = f"https://packages.couchbase.com/releases/{release}/couchbase-server-enterprise-{release}-{test_platform}.{arch}.rpm"
            else:
                platform_link = f"https://packages.couchbase.com/releases/{release}/couchbase-server-enterprise_{release}-{test_platform}_{arch}.deb"
            response = requests.head(platform_link, verify=False, timeout=15)
            if response.status_code != 200:
                continue
            else:
                return platform_link
        return None
