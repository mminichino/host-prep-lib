##
##

import logging
import warnings
import argparse
import sys
import os
import signal
import inspect
import traceback
import datetime
from ansible.cli.galaxy import GalaxyCLI
from datetime import datetime
from pyhostprep.bundles import SoftwareBundle
from pyhostprep.hostinfo import HostInfo
from pyhostprep.software import SoftwareManager
from pyhostprep import constants as C
from pyhostprep import get_config_file, get_data_dir

warnings.filterwarnings("ignore")
logger = logging.getLogger()


def break_signal_handler(signum, frame):
    signal_name = signal.Signals(signum).name
    (filename, line, function, lines, index) = inspect.getframeinfo(frame)
    logger.debug(f"received break signal {signal_name} in {filename} {function} at line {line}")
    tb = traceback.format_exc()
    logger.debug(tb)
    print("")
    print("Break received, aborting.")
    sys.exit(1)


class CustomDisplayFormatter(logging.Formatter):
    FORMATS = {
        logging.DEBUG: f"[{C.GREY_COLOR}{C.FORMAT_LEVEL}{C.SCREEN_RESET}] {C.FORMAT_MESSAGE}",
        logging.INFO: f"[{C.GREEN_COLOR}{C.FORMAT_LEVEL}{C.SCREEN_RESET}] {C.FORMAT_MESSAGE}",
        logging.WARNING: f"[{C.YELLOW_COLOR}{C.FORMAT_LEVEL}{C.SCREEN_RESET}] {C.FORMAT_MESSAGE}",
        logging.ERROR: f"[{C.RED_COLOR}{C.FORMAT_LEVEL}{C.SCREEN_RESET}] {C.FORMAT_MESSAGE}",
        logging.CRITICAL: f"[{C.BOLD_RED_COLOR}{C.FORMAT_LEVEL}{C.SCREEN_RESET}] {C.FORMAT_MESSAGE}"
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        if logging.DEBUG >= logging.root.level:
            log_fmt += C.FORMAT_EXTRA
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)


class CustomLogFormatter(logging.Formatter):
    FORMATS = {
        logging.DEBUG: f"{C.FORMAT_TIMESTAMP} [{C.FORMAT_LEVEL}] {C.FORMAT_MESSAGE}",
        logging.INFO: f"{C.FORMAT_TIMESTAMP} [{C.FORMAT_LEVEL}] {C.FORMAT_MESSAGE}",
        logging.WARNING: f"{C.FORMAT_TIMESTAMP} [{C.FORMAT_LEVEL}] {C.FORMAT_MESSAGE}",
        logging.ERROR: f"{C.FORMAT_TIMESTAMP} [{C.FORMAT_LEVEL}] {C.FORMAT_MESSAGE}",
        logging.CRITICAL: f"{C.FORMAT_TIMESTAMP} [{C.FORMAT_LEVEL}] {C.FORMAT_MESSAGE}"
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        if logging.DEBUG >= logging.root.level:
            log_fmt += C.FORMAT_EXTRA
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)


class StreamToLogger(object):
    def __init__(self, _logger, _level):
        self.logger = _logger
        self.level = _level
        self.buffer = ''

    def write(self, buf):
        for line in buf.rstrip().splitlines():
            self.logger.log(self.level, line.rstrip())

    def flush(self):
        pass


class CLI(object):

    def __init__(self, args):
        signal.signal(signal.SIGINT, break_signal_handler)
        default_debug_file = f"/var/log/hostprep.log"
        debug_file = os.environ.get("DEBUG_FILE", default_debug_file)
        self.args = args
        self.parser = None
        self.config = get_config_file("packages.json")
        self.data = get_data_dir()
        self.op = SoftwareBundle(self.config)
        self.sm = SoftwareManager()
        self.host_info = HostInfo()
        self.host_info.get_service_status()
        self.ansible_galaxy_install()

        if self.args is None:
            self.args = sys.argv

        if sys.stdin and sys.stdin.isatty():
            screen_handler = logging.StreamHandler()
            screen_handler.setFormatter(CustomDisplayFormatter())
            logger.addHandler(screen_handler)

        file_handler = logging.FileHandler(debug_file)
        file_handler.setFormatter(CustomLogFormatter())
        logger.addHandler(file_handler)

    @staticmethod
    def run_timestamp(label: str):
        timestamp = datetime.utcnow().strftime("%b %d %H:%M:%S")
        logger.info(f" ==== Run {label} {timestamp} ====")

    @staticmethod
    def ansible_galaxy_install():
        args = ["ansible-galaxy", "collection", "install", "community.general"]
        GalaxyCLI.cli_executor(args)
        args = ["ansible-galaxy", "collection", "install", "ansible.posix"]
        GalaxyCLI.cli_executor(args)

    def init_parser(self):
        self.parser = argparse.ArgumentParser(add_help=False)
