##
##

from __future__ import annotations
import attr
import json
from typing import Optional, List
from pyhostprep.osinfo import OSRelease


class BundleManagerError(Exception):
    pass


@attr.s
class Bundle:
    name: Optional[str] = attr.ib(default=None)
    requires: Optional[List[str]] = attr.ib(default=None, metadata={'pk': True})
    pre: Optional[str] = attr.ib(default=None)
    run: Optional[str] = attr.ib(default=None)
    post: Optional[str] = attr.ib(default=None)
    extra_vars: Optional[List[str]] = attr.ib(default=[])

    @property
    def get_values(self):
        return self.__annotations__

    @property
    def as_dict(self):
        return self.__dict__

    @classmethod
    def from_dict(cls, name: str, json_data: dict):
        return cls(
            name,
            json_data.get("requires"),
            json_data.get("pre"),
            json_data.get("run"),
            json_data.get("post"),
            json_data.get("extra_vars", []),
        )


class SoftwareBundle(object):

    def __init__(self, packages: str = "config/packages.json", os_release: str = "/etc/os-release"):
        try:
            self.os = OSRelease(os_release)
            with open(packages, 'r') as in_file:
                self.packages = json.load(in_file)
        except Exception as err:
            raise BundleManagerError(err)
        self.bundle_list: List[Bundle] = []

    def add(self, bundle_name: str):
        bundle = self.get(bundle_name)
        self.bundle_list.append(bundle)

    def get(self, bundle_name: str) -> Bundle:
        bundle_data = self.packages.get("bundles", {}).get(bundle_name, {})
        for all_os, data in bundle_data.items():
            os_list = all_os.split('|')
            if self.os.os_name in os_list:
                return Bundle.from_dict(bundle_name, data)
        raise BundleManagerError(f"bundle {bundle_name} not found for os {self.os.os_name}")

    def install_list(self) -> List[Bundle]:
        to_install = []
        for bundle in self.bundle_list:
            if len(bundle.requires) > 0:
                for b in bundle.requires:
                    to_install.append(b)
            to_install.append(bundle.name)
        seen = set()
        return [self.get(e) for e in to_install if not (e in seen or seen.add(e))]
