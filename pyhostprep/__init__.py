import os

_ROOT = os.path.abspath(os.path.dirname(__file__))
__version__ = "2.0.0"
VERSION = __version__


def get_playbook_file(file):
    return os.path.join(_ROOT, 'data', 'playbooks', file)


def get_config_file(file):
    return os.path.join(_ROOT, 'data', 'config', file)


def get_data_dir():
    return os.path.join(_ROOT, 'data')
