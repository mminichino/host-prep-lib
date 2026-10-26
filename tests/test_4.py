#!/usr/bin/env python3

import json
import logging
import warnings

import pytest

from pyhostprep.storage import StorageManager

warnings.filterwarnings("ignore")
logger = logging.getLogger()


GCP_HYPERDISK = {
    "blockdevices": [
        {
            "name": "loop0",
            "type": "loop",
            "mountpoints": ["/snap/core24/2124"],
        },
        {
            "name": "nvme0n1",
            "type": "disk",
            "mountpoints": [None],
            "children": [
                {"name": "nvme0n1p1", "type": "part", "mountpoints": ["/"]},
                {"name": "nvme0n1p15", "type": "part", "mountpoints": ["/boot/efi"]},
            ],
        },
        {
            "name": "nvme0n2",
            "type": "disk",
            "mountpoints": [None],
        },
    ]
}

AWS_NVME = {
    "blockdevices": [
        {"name": "nvme0n1", "type": "disk"},
        {"name": "nvme1n1", "type": "disk"},
        {"name": "nvme2n1", "type": "disk"},
    ]
}

SCSI_DISKS = {
    "blockdevices": [
        {"name": "sda", "type": "disk", "children": [{"name": "sda1", "type": "part"}]},
        {"name": "sdb", "type": "disk"},
    ]
}


class _FakeEbsNvmeDevice:
    def __init__(self, device, names):
        self.device = device
        outcome = names.get(device, OSError(device))
        if isinstance(outcome, Exception):
            raise outcome
        self._name = outcome

    def get_block_device(self, stripped=False):
        return self._name


def _manager(monkeypatch, blockdevices, names):
    payload = json.dumps({"blockdevices": blockdevices})

    def cmd_output(command, directory, split=False, split_sep=None, no_raise=False):
        return payload.splitlines()

    monkeypatch.setattr("pyhostprep.storage.RunShellCommand.cmd_output", staticmethod(cmd_output))

    def factory(device):
        return _FakeEbsNvmeDevice(device, names)

    monkeypatch.setattr("pyhostprep.storage.EbsNvmeDevice", factory)
    return StorageManager()


@pytest.mark.unit_test
def test_gcp_hyperdisk_nvme_uses_namespace_as_disk_index(monkeypatch):
    not_ebs = TypeError("Not an EBS device")
    manager = _manager(
        monkeypatch,
        GCP_HYPERDISK["blockdevices"],
        {
            "/dev/nvme0n1": not_ebs,
            "/dev/nvme0n2": not_ebs,
        },
    )

    assert manager.get_device(1) == "/dev/nvme0n1"
    assert manager.get_device(2) == "/dev/nvme0n2"
    assert manager.get_device(3) is None
    assert [device["name"] for device in manager.device_list] == ["/dev/nvme0n1", "/dev/nvme0n2"]


@pytest.mark.unit_test
def test_gcp_hyperdisk_nvme_matches_when_identify_ioctl_fails(monkeypatch):
    manager = _manager(
        monkeypatch,
        GCP_HYPERDISK["blockdevices"],
        {
            "/dev/nvme0n1": OSError("ioctl failed"),
            "/dev/nvme0n2": OSError("ioctl failed"),
        },
    )

    assert manager.get_device(2) == "/dev/nvme0n2"


@pytest.mark.unit_test
def test_aws_ebs_nvme_still_uses_virtual_device_letter(monkeypatch):
    manager = _manager(
        monkeypatch,
        AWS_NVME["blockdevices"],
        {
            "/dev/nvme0n1": "none",
            "/dev/nvme1n1": "xvda",
            "/dev/nvme2n1": "/dev/xvdb",
        },
    )

    assert manager.get_device(1) == "/dev/nvme1n1"
    assert manager.get_device(2) == "/dev/nvme2n1"


@pytest.mark.unit_test
def test_scsi_disk_letter_is_unchanged(monkeypatch):
    manager = _manager(monkeypatch, SCSI_DISKS["blockdevices"], {})

    assert manager.get_device(1) == "/dev/sda"
    assert manager.get_device(2) == "/dev/sdb"
    assert manager.get_partition("/dev/sda", 1) == "/dev/sda1"
