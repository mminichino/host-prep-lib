##
##

import json
from pyhostprep.command import RunShellCommand, RCNotZero
from pyhostprep.ebsnvme import ebs_nvme_device


class StorageMgrError(Exception):
    pass


class StorageManager(object):

    def __init__(self):
        self.device_list = []
        cmd = ["lsblk", "--json"]

        try:
            output = RunShellCommand().cmd_output(cmd, "/var/tmp")
        except RCNotZero as err:
            raise StorageMgrError(f"can not get disk info: {err}")

        disk_data = json.loads('\n'.join(output))

        for device in disk_data.get('blockdevices', []):
            if device.get('type') == "loop":
                continue
            if device.get('children') is not None:
                continue
            if device.get('mountpoints', [])[0] is not None:
                continue
            device_name = f"/dev/{device['name']}"
            self.device_list.append(device_name)

    def get_device(self, index: int = 1):
        for device in self.device_list:
            try:
                dev = ebs_nvme_device(device)
                name = dev.get_block_device(stripped=True)
                check_name = f"/dev/{name}"
            except OSError:
                check_name = device

            if check_name[-1] == chr(ord('`') + index):
                return device

        return None
