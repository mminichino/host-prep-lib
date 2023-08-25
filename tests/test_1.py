#!/usr/bin/env python3

import os
import logging
import warnings
import pytest
from tests.common import start_container, stop_container, run_in_container, container_log, copy_log_from_container, image_name, copy_to_container

warnings.filterwarnings("ignore")
logger = logging.getLogger()
current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)


@pytest.mark.parametrize("container, platform", [("rhel-8-init", "linux/amd64"),
                                                 ("rhel-9-init", "linux/amd64"),
                                                 ("rocky-8-init", "linux/amd64"),
                                                 ("rocky-9-init", "linux/amd64"),
                                                 ("oel-8-init", "linux/amd64"),
                                                 ("oel-9-init", "linux/amd64"),
                                                 ("fedora-init", "linux/amd64"),
                                                 ("ubuntu-focal-init", "linux/amd64"),
                                                 ("ubuntu-jammy-init", "linux/amd64"),
                                                 ("debian-bullseye-init", "linux/amd64"),
                                                 ("opensuse-init", "linux/amd64"),
                                                 ("sles-155-init", "linux/amd64"),
                                                 ("sles-153-init", "linux/amd64"),
                                                 ("amazon-2-init", "linux/amd64"),
                                                 ("amazon-2023-init", "linux/amd64")])
def test_1(container, platform):
    global parent
    volume = "/opt/couchbase"
    destination = "/var/tmp"
    hostprep_log_file = "/var/log/hostprep.log"
    setup_log_file = "/usr/local/hostprep/setup.log"
    setup_script = os.path.join(parent, 'bin', 'setup.sh')

    container_id = start_container(container, platform, volume)
    log_dest = f"{parent}/tests/output/{image_name(container_id)}"
    try:
        copy_to_container(container_id, setup_script, destination)
        run_in_container(container_id, destination, ["./setup.sh", "-s", "-g", "https://github.com/mminichino/host-prep-lib"])
        run_in_container(container_id, destination, ["bundlemgr", "-b", "CBS"])
        stop_container(container_id)
    except Exception:
        container_log(container_id, log_dest)
        copy_log_from_container(container_id, hostprep_log_file, log_dest)
        copy_log_from_container(container_id, setup_log_file, log_dest)
        stop_container(container_id)
        raise
