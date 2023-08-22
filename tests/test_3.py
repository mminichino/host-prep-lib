#!/usr/bin/env python3

import os
import logging
import warnings
from py_host_prep.hostpreplib.bundles import SoftwareBundle

warnings.filterwarnings("ignore")
logger = logging.getLogger()
current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)


def test_os_release_1():
    bundles = SoftwareBundle(f"{parent}/test/packages.json", f"{parent}/test/os-release")
    bundles.add("TestB")
    bundles.add("TestC")
    bundles.add("TestD")
    bundles.add("TestE")
    to_install = bundles.install_list()
    install_list = [e.name for e in to_install]
    assert install_list == ['Base', 'TestA', 'TestB', 'TestC', 'TestD', 'TestE']
