##
##

from typing import Union, List
import subprocess
import logging
import io

logger = logging.getLogger('hostprep.shell')
logger.addHandler(logging.NullHandler())


class ShellCommandError(Exception):
    pass


class RunShellCommand(object):

    def __init__(self):
        pass

    @staticmethod
    def cmd_exec(command: Union[str, List[str]], directory: str):
        buffer = io.BytesIO()
        logger.debug(f"Shell command: {' '.join(command)}")

        p = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, cwd=directory)

        while True:
            data = p.stdout.read()
            if not data:
                break
            buffer.write(data)

        p.communicate()

        if p.returncode != 0:
            raise ShellCommandError("command exited with non-zero return code")

        buffer.seek(0)
        return buffer
