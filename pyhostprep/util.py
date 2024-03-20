##
##

import os
import glob
from pwd import getpwnam
from grp import getgrnam


class FileManager(object):

    def __init__(self):
        pass

    def make_dir(self, name: str, owner: str = None, group: str = None, mode: int = 0o775):
        owner_id = getpwnam(owner).pw_uid if owner else None
        group_id = getgrnam(group).gr_gid if group else None
        if not os.path.exists(name):
            path_dir = os.path.dirname(name)
            if not os.path.exists(path_dir):
                self.make_dir(path_dir)
            try:
                uid = os.stat(path_dir).st_uid if not owner_id else owner_id
                gid = os.stat(path_dir).st_gid if not group_id else group_id
                os.mkdir(name)
                os.chown(name, uid, gid)
                os.chmod(name, mode)
            except OSError:
                raise

    def set_perms(self, name: str, owner: str = None, group: str = None, mode: int = 0o775):
        owner_id = getpwnam(owner).pw_uid if owner else None
        group_id = getgrnam(group).gr_gid if group else None
        if os.path.exists(name):
            path_dir = os.path.dirname(name)
            if path_dir:
                uid = os.stat(path_dir).st_uid if not owner_id else owner_id
                gid = os.stat(path_dir).st_gid if not group_id else group_id
                os.chown(name, uid, gid)
            os.chmod(name, mode)
        else:
            self.make_dir(name, owner, group, mode)

    @staticmethod
    def find_file(name: str, path: str):
        full_path = os.path.join(path, name)
        result = glob.glob(full_path)
        return result[0] if len(result) > 0 else None

    @staticmethod
    def file_append(filename: str, line: str):
        with open(filename, 'a') as file:
            file.write(f"{line}\n")

    @staticmethod
    def file_search(filename: str, line: str):
        if line in open(filename, 'r').read():
            return True
        return False
