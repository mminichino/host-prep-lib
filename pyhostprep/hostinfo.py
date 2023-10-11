##
##
import os.path

from pyhostprep.command import RunShellCommand, ShellCommandError
from io import BytesIO
from typing import Optional, List
import attr
import shutil


@attr.s
class Service:
    name: Optional[str] = attr.ib(default=None)
    loaded: Optional[str] = attr.ib(default=None)
    state: Optional[str] = attr.ib(default=None)
    status: Optional[str] = attr.ib(default=None)

    @property
    def get_values(self):
        return self.__annotations__

    @property
    def as_dict(self):
        return self.__dict__

    @classmethod
    def create(cls, name: str, loaded: str, state: str, status: str):
        return cls(
            name,
            loaded,
            state,
            status
        )


@attr.s
class System:
    services: List[Service] = attr.ib()

    @classmethod
    def create(cls):
        return cls(
            []
        )

    def service(self, name: str, loaded: str, state: str, status: str):
        service = Service.create(name, loaded, state, status)
        self.services.append(service)
        return self

    @property
    def all_services(self):
        return [(s.name, s.status) for s in self.services]

    def is_running(self, name: str) -> bool:
        name = f"{name}.service"
        result = next((s for s in self.services if s.name == name and s.status == 'running'), None)
        return result is not None


class HostInfo(object):

    def __init__(self):
        self._system = System.create()

    @property
    def system(self):
        return self._system

    def get_service_status(self):
        if not shutil.which("systemctl"):
            return

        check_command = ["ps", "--no-headers", "-o", "comm", "1"]

        try:
            output: BytesIO = RunShellCommand().cmd_exec(check_command, "/var/tmp")
            result = output.readline().decode("utf-8").strip()
            entrypoint = os.path.basename(result)
            if entrypoint != 'init' and entrypoint != 'systemd':
                return
        except ShellCommandError:
            raise

        command = ["systemctl", "list-units", "--type=service", "--no-pager", "--no-legend"]

        try:
            output: BytesIO = RunShellCommand().cmd_exec(command, "/var/tmp")
        except ShellCommandError:
            raise

        while True:
            line = output.readline()
            if not line:
                break
            line_string = line.decode("utf-8")
            items = line_string.strip().split()
            if len(items) >= 4:
                self._system.service(items[0], items[1], items[2], items[3])
