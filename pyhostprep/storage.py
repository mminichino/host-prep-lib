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
            device_name = f"/dev/{device['name']}"
            part_list = []
            if device.get('children'):
                part_list = [p.get('name') for p in device.get('children')]
            self.device_list.append(dict(name=device_name, partitions=part_list))

    def get_device(self, index: int = 1):
        for device in [d.get('name') for d in self.device_list]:
            try:
                dev = ebs_nvme_device(device)
                name = dev.get_block_device(stripped=True)
                check_name = f"/dev/{name}"
            except OSError:
                check_name = device

            if check_name[-1] == chr(ord('`') + index):
                return device

        return None

    def get_partition(self, dev: str, number: int = 1):
        for device in self.device_list:
            if device.get('name') == dev:
                if len(device.get('partitions')) >= number:
                    part_dev = device.get('partitions')[number - 1]
                    return f"/dev/{part_dev}"
        return None
