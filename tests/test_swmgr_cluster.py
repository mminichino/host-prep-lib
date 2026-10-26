#!/usr/bin/env python3
#
import os
from pathlib import Path

import pytest

from pyhostprep.certificates import CertMgr
from tests.couchbase_test_utils import (
    ADMIN_PASSWORD,
    ADMIN_USER,
    CLUSTER_NAME,
    assert_cluster_initialized,
    copy_ca_files,
    exec_swmgr,
    install_pyhostprep,
    start_couchbase_container,
    trusted_ca_count,
)

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)


@pytest.mark.integration
def test_swmgr_cluster_create_default_ca():
    container = start_couchbase_container()
    try:
        install_pyhostprep(container, Path(parent))

        exit_code, output = exec_swmgr(
            container,
            [
                "cluster",
                "-n",
                CLUSTER_NAME,
                "-u",
                ADMIN_USER,
                "-p",
                ADMIN_PASSWORD,
                "create",
            ],
        )

        assert exit_code == 0, output
        assert "Success: Cluster Initialized" in output
        assert_cluster_initialized(container)
        assert trusted_ca_count(container) >= 1
    finally:
        container.stop()


@pytest.mark.integration
def test_swmgr_cluster_create_custom_ca():
    container = start_couchbase_container()
    try:
        install_pyhostprep(container, Path(parent))

        key_bytes, cert_bytes = CertMgr().certificate_ca()
        copy_ca_files(container, key_bytes.decode("utf-8"), cert_bytes.decode("utf-8"))

        exit_code, output = exec_swmgr(
            container,
            [
                "cluster",
                "-n",
                CLUSTER_NAME,
                "-u",
                ADMIN_USER,
                "-p",
                ADMIN_PASSWORD,
                "create",
            ],
        )

        assert exit_code == 0, output
        assert "Success: Cluster Initialized" in output
        assert "Success: Node certificate updated" in output
        assert_cluster_initialized(container)
        assert trusted_ca_count(container) >= 2
    finally:
        container.stop()
