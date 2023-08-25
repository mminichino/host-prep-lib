#!/usr/bin/env python3

import os
import argparse
import logging
import warnings
from common import (start_container, stop_container, run_in_container, get_container_id, container_mkdir, container_log, copy_log_from_container, image_name,
                    copy_git_to_container, copy_to_container)

warnings.filterwarnings("ignore")
logger = logging.getLogger()
current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)


class Params(object):

    def __init__(self):
        parser = argparse.ArgumentParser()
        parser.add_argument("--container", action="store", help="Container", default="redhat/ubi8")
        parser.add_argument("--script", action="store", help="Script", default="setup.sh")
        parser.add_argument("--log", action="store", help="Script", default="setup.log")
        parser.add_argument("--run", action="store_true")
        parser.add_argument("--start", action="store_true")
        parser.add_argument("--stop", action="store_true")
        parser.add_argument("--refresh", action="store_true")
        parser.add_argument("--minimal", action="store_true")
        parser.add_argument("--logs", action="store_true")
        parser.add_argument("--arm", action="store_true")
        self.args = parser.parse_args()

    @property
    def parameters(self):
        return self.args


def minimal_1(args: argparse.Namespace):
    start_container(args.container)


def manual_1(args: argparse.Namespace):
    global parent
    if args.arm:
        platform = "linux/arm64"
    else:
        platform = "linux/amd64"
    volume = "/opt/couchbase"
    destination = "/usr/local/hostprep"

    container_id = start_container(args.container, platform, volume)
    try:
        container_mkdir(container_id, destination)
        copy_git_to_container(container_id, parent, destination)
        run_in_container(container_id, destination, ["bin/setup.sh", "-s"])
    except Exception:
        raise


def manual_2(args: argparse.Namespace):
    global parent
    if args.arm:
        platform = "linux/arm64"
    else:
        platform = "linux/amd64"
    volume = "/opt/couchbase"
    destination = "/var/tmp"
    container_image = args.container
    hostprep_log_file = "/var/log/hostprep.log"
    setup_log_file = "/var/tmp/setup.log"
    setup_script = os.path.join(parent, 'bin', 'setup.sh')

    container_id = start_container(container_image, platform, volume)
    log_dest = f"{parent}/tests/output/{image_name(container_id)}"
    try:
        copy_to_container(container_id, setup_script, destination)
        run_in_container(container_id, destination, ["./setup.sh", "-s", "-g", "https://github.com/mminichino/host-prep-lib"])
        run_in_container(container_id, destination, ["bundlemgr", "-b", "CBS"])
    except Exception:
        container_log(container_id, log_dest)
        copy_log_from_container(container_id, hostprep_log_file, log_dest)
        copy_log_from_container(container_id, setup_log_file, log_dest)
        raise


def get_logs():
    global parent
    container_id = get_container_id()
    hostprep_log_file = "/var/log/hostprep.log"
    setup_log_file = "/usr/local/hostprep/setup.log"
    log_dest = f"{parent}/tests/output/{image_name(container_id)}"
    container_log(container_id, log_dest)
    copy_log_from_container(container_id, hostprep_log_file, log_dest)
    copy_log_from_container(container_id, setup_log_file, log_dest)


def refresh():
    global parent
    destination = "/usr/local/hostprep"

    container_id = get_container_id()
    try:
        copy_git_to_container(container_id, parent, destination)
    except Exception:
        raise


p = Params()
options = p.parameters

try:
    debug_level = int(os.environ['DEBUG_LEVEL'])
except (ValueError, KeyError):
    debug_level = 3

if debug_level == 0:
    logger.setLevel(logging.DEBUG)
elif debug_level == 1:
    logger.setLevel(logging.ERROR)
elif debug_level == 2:
    logger.setLevel(logging.INFO)
else:
    logger.setLevel(logging.CRITICAL)

logging.basicConfig()

if options.stop:
    container = get_container_id()
    if container:
        stop_container(container)

if options.run:
    manual_1(options)

if options.start:
    manual_2(options)

if options.refresh:
    refresh()

if options.minimal:
    minimal_1(options)

if options.logs:
    get_logs()
