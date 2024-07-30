##
##

import os
import glob
from pwd import getpwnam
from grp import getgrnam
from shutil import copyfile
from pathlib import PosixPath


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

    def copy_file(self, src: str, dest: str, owner: str = None, group: str = None, mode: int = 0o775):
        path_dir = os.path.dirname(dest)
        owner_id = getpwnam(owner).pw_uid if owner else None
        group_id = getgrnam(group).gr_gid if group else None

        if not os.path.exists(path_dir):
            self.make_dir(path_dir, owner, group, mode)

        copyfile(src, dest)

        uid = os.stat(path_dir).st_uid if not owner_id else owner_id
        gid = os.stat(path_dir).st_gid if not group_id else group_id

        os.chown(dest, uid, gid)
        os.chmod(dest, mode)

    def write_file(self, data: str, dest: str, owner: str = None, group: str = None, mode: int = 0o775):
        path_dir = os.path.dirname(dest)
        owner_id = getpwnam(owner).pw_uid if owner else None
        group_id = getgrnam(group).gr_gid if group else None

        if not os.path.exists(path_dir):
            self.make_dir(path_dir, owner, group, mode)

        with open(dest, 'w') as f:
            f.write(data)

        uid = os.stat(path_dir).st_uid if not owner_id else owner_id
        gid = os.stat(path_dir).st_gid if not group_id else group_id

        os.chown(dest, uid, gid)
        os.chmod(dest, mode)

    @staticmethod
    def get_user_home():
        username = os.getlogin()
        p = PosixPath(f"~{username}")
        return str(p.expanduser().absolute())

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
