##
##

from socket import getaddrinfo, gethostname
from requests import get
import requests.exceptions
import warnings
import socket


class NetworkInfo(object):

    def __init__(self):
        warnings.filterwarnings("ignore")

    @staticmethod
    def get_ip_address(ip_proto: str = "ipv4"):
        af_inet = 2
        if ip_proto == "ipv6":
            af_inet = 30
        system_ip_list = getaddrinfo(gethostname(), None, af_inet, 1, 0)
        ip = system_ip_list[0][4][0]
        return ip

    @staticmethod
    def get_pubic_ip_address():
        try:
            ip = get('https://api.ipify.org', timeout=4).text
            return ip
        except requests.exceptions.Timeout:
            return None

    @staticmethod
    def check_port(address: str, port: int):
        socket.setdefaulttimeout(4)
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex((address, port))
        sock.close()
        if result == 0:
            return True
        else:
            return False