##
##

import io
import tarfile
from pathlib import Path
from typing import Iterable, Sequence

import docker
import pytest
from testcontainers.core.container import DockerContainer
from testcontainers.core.wait_strategies import HttpWaitStrategy

COUCHBASE_IMAGE = "couchbase/server:enterprise-8.0.2"
CLUSTER_NAME = "swmgr-pytest"
ADMIN_USER = "Administrator"
ADMIN_PASSWORD = "password"
PROJECT_DIR = "host-prep-lib"
PROJECT_MOUNT = f"/opt/{PROJECT_DIR}"


def require_docker() -> None:
    try:
        docker.from_env().ping()
    except Exception as exc:
        pytest.skip(f"Docker is not available: {exc}")


def start_couchbase_container() -> DockerContainer:
    require_docker()
    container = DockerContainer(COUCHBASE_IMAGE)
    container.with_exposed_ports(8091)
    container.waiting_for(
        HttpWaitStrategy(8091, "/ui/index.html")
        .for_status_code(200)
        .with_startup_timeout(180)
    )
    container.start()
    return container


def _put_files(container: DockerContainer, destination: str, files: Iterable[tuple[Path, str]]) -> None:
    stream = io.BytesIO()
    with tarfile.open(fileobj=stream, mode="w") as tar:
        for source, arcname in files:
            tar.add(source, arcname=arcname)
    wrapped = container.get_wrapped_container()
    if not wrapped.put_archive(destination, stream.getvalue()):
        raise RuntimeError(f"Failed to copy files into container at {destination}")


def install_pyhostprep(container: DockerContainer, project_root: Path) -> None:
    install_pip(container)
    _put_files(
        container,
        "/opt",
        [
            (project_root / "pyhostprep", f"{PROJECT_DIR}/pyhostprep"),
            (project_root / "pyproject.toml", f"{PROJECT_DIR}/pyproject.toml"),
            (project_root / "README.md", f"{PROJECT_DIR}/README.md"),
        ],
    )
    result = container.exec(
        ["pip3", "install", "--break-system-packages", PROJECT_MOUNT]
    )
    if result.exit_code != 0:
        raise RuntimeError(result.output.decode())


def install_pip(container: DockerContainer) -> None:
    result = container.exec(
        [
            "bash",
            "-lc",
            "apt-get update -qq && DEBIAN_FRONTEND=noninteractive "
            "apt-get install -y -qq python3-pip",
        ]
    )
    if result.exit_code != 0:
        raise RuntimeError(result.output.decode())


def copy_ca_files(container: DockerContainer, ca_key_pem: str, ca_cert_pem: str) -> None:
    stream = io.BytesIO()
    with tarfile.open(fileobj=stream, mode="w") as tar:
        for name, content in (("ca.key", ca_key_pem), ("ca.pem", ca_cert_pem)):
            data = content.encode("utf-8")
            info = tarfile.TarInfo(name=name)
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
    wrapped = container.get_wrapped_container()
    if not wrapped.put_archive("/root", stream.getvalue()):
        raise RuntimeError("Failed to copy CA files into container")


def exec_swmgr(container: DockerContainer, args: Sequence[str]) -> tuple[int, str]:
    command = ["swmgr", *args]
    result = container.exec(command)
    return result.exit_code, result.output.decode()


def assert_cluster_initialized(container: DockerContainer) -> None:
    result = container.exec(
        [
            "/opt/couchbase/bin/couchbase-cli",
            "setting-cluster",
            "--cluster",
            "127.0.0.1",
            "--username",
            ADMIN_USER,
            "--password",
            ADMIN_PASSWORD,
        ]
    )
    assert result.exit_code == 0, result.output.decode()
    assert "SUCCESS" in result.output.decode()


def trusted_ca_count(container: DockerContainer) -> int:
    result = container.exec(
        [
            "bash",
            "-lc",
            "curl -s -u Administrator:password http://127.0.0.1:8091/pools/default/trustedCAs "
            "| python3 -c \"import sys, json; print(len(json.load(sys.stdin)))\"",
        ]
    )
    assert result.exit_code == 0, result.output.decode()
    return int(result.output.decode().strip())
