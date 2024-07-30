##
##

import csv
import os
import plistlib
from pyhostprep.osfamily import OSFamily


class OSRelease(object):
    debian_arch_map = {
        'aarch64': 'arm64',
        'x86_64': 'amd64'
    }

    def __init__(self, filename: str = "/etc/os-release"):
        self.os_release = filename
        self.macos_release = "/System/Library/CoreServices/SystemVersion.plist"
        self.os_info = {}
        self.os_name = None
        self.os_like = None
        self.arch = None
        self.os_major_release = None
        self.os_minor_release = None

        self.as_dict()
        self.os_name = self.os_info['ID']
        like_string = self.os_info.get('ID_LIKE', self.os_name)
        self.os_like = like_string.split()[0]
        self.arch = os.uname().machine
        self.os_major_release = self.os_info['VERSION_ID'].split('.')[0]
        try:
            self.os_minor_release = self.os_info['VERSION_ID'].split('.')[1]
        except IndexError:
            pass

    def as_dict(self):
        if os.path.exists(self.os_release):
            with open(self.os_release) as data:
                reader = csv.reader(data, delimiter="=")
                for rows in reader:
                    if len(rows) < 2:
                        continue
                    self.os_info.update({rows[0]: rows[1]})
        elif os.path.exists(self.macos_release):
            with open(self.macos_release, 'rb') as f:
                sys_info = plistlib.load(f)
            self.os_info['NAME'] = os.uname().sysname
            self.os_info['VERSION'] = os.uname().version
            self.os_info['ID'] = sys_info.get('ProductName')
            self.os_info['VERSION_ID'] = sys_info.get('ProductVersion')

    @property
    def os_id(self):
        return self.os_name

    @property
    def major_rel(self):
        return int(self.os_major_release)

    @property
    def minor_rel(self):
        return int(self.os_minor_release)

    @property
    def os_family(self):
        return self.os_like

    @property
    def architecture(self):
        if self.os_family == 'debian':
            return OSRelease.debian_arch_map.get(self.arch, self.arch)
        else:
            return self.arch

    @property
    def machine(self):
        return self.arch

    @property
    def family(self):
        if os.path.exists(self.os_release):
            return OSFamily.LINUX
        elif os.path.exists(self.macos_release):
            return OSFamily.MACOS
        elif os.name == 'nt':
            return OSFamily.WINDOWS
        else:
            return OSFamily.UNKNOWN
