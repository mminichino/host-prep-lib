#!/usr/bin/env python3

import os
import logging
import warnings
import pytest
from hostpreplib.osinfo import OSRelease

warnings.filterwarnings("ignore")
logger = logging.getLogger()
current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)


@pytest.mark.parametrize("file_name, os_id, major, minor", [("os-release1", "ubuntu", 20, 4), ("os-release2", "rhel", 9, 2)])
def test_os_release_1(file_name, os_id, major, minor):
    os_obj = OSRelease(f"{parent}/test/{file_name}")
    assert os_obj.os_name == os_id
    assert os_obj.major_rel == major
    assert os_obj.minor_rel == minor
