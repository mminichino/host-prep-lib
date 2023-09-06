##
##

import json
from pyhostprep.command import RunShellCommand, RCNotZero


class StorageMgrError(Exception):
    pass


class StorageManager(object):

    def __init__(self):
        device_list = []
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
            print(device_name)
