##
##

import socket
import datetime
from typing import List
from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.serialization import load_pem_private_key
from cryptography.x509.oid import NameOID


class CertMgr(object):

    def __init__(self):
        pass

    @staticmethod
    def private_key(filename: str, size=2048):
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=size,
            backend=default_backend()
        )
        pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        ).decode()
        with open(filename, 'w') as f:
            f.write(pem)

    @staticmethod
    def certificate_hostname(filename: str, private_key: str, domain_name: str = None, alt_name: List[str] = None):
        one_day = datetime.timedelta(1, 0, 0)
        with open(private_key, 'r') as pem_in:
            privkey = pem_in.read()
        private_key = load_pem_private_key(privkey.encode(), None, default_backend())
        public_key = private_key.public_key()

        cert_name = x509.Name([
            x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
            x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "California"),
            x509.NameAttribute(NameOID.LOCALITY_NAME, "Santa Clara"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Couchbase")
        ])

        builder = x509.CertificateBuilder()
        builder = builder.subject_name(cert_name)
        builder = builder.issuer_name(cert_name)
        builder = builder.not_valid_before(datetime.datetime.today() - one_day)
        builder = builder.not_valid_after(datetime.datetime.today() + (one_day * 365 * 10))
        builder = builder.serial_number(x509.random_serial_number())
        builder = builder.public_key(public_key)

        host_names = []

        if alt_name is not None:
            for name in alt_name:
                host_names.append(x509.DNSName(name))

        if domain_name is not None:
            host_names.append(x509.DNSName(f"*.{domain_name}"))

        host_names.extend([
            x509.DNSName(socket.gethostname()),
            x509.DNSName('127.0.0.1'),
            x509.DNSName('localhost')
        ])

        builder = builder.add_extension(x509.SubjectAlternativeName(host_names), critical=False)
        builder = builder.add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)

        certificate = builder.sign(private_key=private_key, algorithm=hashes.SHA256(), backend=default_backend())

        cert = certificate.public_bytes(serialization.Encoding.PEM).decode('utf-8')
        with open(filename, 'w') as f:
            f.write(cert)

    @staticmethod
    def certificate_basic(filename: str, private_key: str):
        one_day = datetime.timedelta(1, 0, 0)
        with open(private_key, 'r') as pem_in:
            privkey = pem_in.read()
        private_key = load_pem_private_key(privkey.encode(), None, default_backend())
        public_key = private_key.public_key()

        cert_name = x509.Name([
            x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
            x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "California"),
            x509.NameAttribute(NameOID.LOCALITY_NAME, "Santa Clara"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Couchbase")
        ])

        builder = x509.CertificateBuilder()
        builder = builder.subject_name(cert_name)
        builder = builder.issuer_name(cert_name)
        builder = builder.not_valid_before(datetime.datetime.today() - one_day)
        builder = builder.not_valid_after(datetime.datetime.today() + (one_day * 365 * 10))
        builder = builder.serial_number(x509.random_serial_number())
        builder = builder.public_key(public_key)

        certificate = builder.sign(private_key=private_key, algorithm=hashes.SHA256(), backend=default_backend())

        cert = certificate.public_bytes(serialization.Encoding.PEM).decode('utf-8')
        with open(filename, 'w') as f:
            f.write(cert)
