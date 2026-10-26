##
##

import logging
import os
import signal
import sys
import warnings
from dataclasses import dataclass
from typing import Annotated, List, Optional

import typer

from pyhostprep.certificates import CertMgr
from pyhostprep.gateway import GatewayConfig, SyncGateway
from pyhostprep.models import IndexMemoryOption, ServerConfig
from pyhostprep.network import NetworkInfo
from pyhostprep.server import CouchbaseServer
from pyhostprep.util import FileManager

warnings.filterwarnings("ignore")
logger = logging.getLogger()

app = typer.Typer(add_completion=False, no_args_is_help=True)
cluster_app = typer.Typer(no_args_is_help=True)
gateway_app = typer.Typer(no_args_is_help=True)
cert_app = typer.Typer(no_args_is_help=True)

app.add_typer(cluster_app, name="cluster")
app.add_typer(gateway_app, name="gateway")
app.add_typer(cert_app, name="cert")


def _break_signal_handler(signum, _):
    logger.debug(f"Received {signum} signal")
    print("")
    print("Break received, aborting.")
    raise SystemExit(1)


def _setup_logging(debug: bool = False) -> None:
    signal.signal(signal.SIGINT, _break_signal_handler)

    log_file_name = f"{os.path.splitext(os.path.basename(sys.argv[0]))[0]}.log"
    if os.access("/var/log", os.W_OK):
        debug_file = f"/var/log/{log_file_name}"
    elif "HOME" in os.environ:
        log_dir = os.path.join(os.environ["HOME"], ".log")
        FileManager().make_dir(log_dir)
        debug_file = f"{log_dir}/{log_file_name}"
    else:
        debug_file = f"/tmp/{log_file_name}"
    debug_file = os.environ.get("DEBUG_FILE", debug_file)

    if sys.stdin and sys.stdin.isatty():
        screen_handler = logging.StreamHandler()
        screen_handler.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
        logger.addHandler(screen_handler)

    file_handler = logging.FileHandler(debug_file)
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    )
    logger.addHandler(file_handler)
    logger.setLevel(logging.DEBUG if debug else logging.INFO)


def _parse_csv(value: str) -> List[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _resolve_ip_address(ip_address: Optional[str]) -> str:
    if ip_address:
        return ip_address
    try:
        return NetworkInfo().get_ip_address()
    except Exception as e:
        logger.debug(f"Fallback to localhost: {e}")
        return "127.0.0.1"


def _build_server_config(
    name: str,
    ip_address: Optional[str],
    rally_ip_address: Optional[str],
    external_ip_address: Optional[str],
    services: str,
    username: str,
    password: str,
    index_mem: str,
    server_group: str,
    data_path: str,
    community: bool,
    private_key: Optional[str],
    options: Optional[str],
    ca_cert: Optional[str] = None,
    ca_cert_key: Optional[str] = None,
) -> ServerConfig:
    services_list = _parse_csv(services)
    services_list = ["fts" if service == "search" else service for service in services_list]
    options_list = _parse_csv(options) if options else []
    resolved_ip = _resolve_ip_address(ip_address)
    index_mem_opt = IndexMemoryOption.memopt if "memopt" in options_list else IndexMemoryOption[index_mem]

    return ServerConfig(
        name=name,
        ip_address=resolved_ip,
        rally_ip_address=rally_ip_address or resolved_ip,
        external_ip_address=external_ip_address,
        services=services_list,
        username=username,
        password=password,
        index_mem_opt=index_mem_opt,
        server_group=server_group,
        data_path=data_path,
        community_edition=community,
        private_key=private_key,
        options=options_list,
        ca_cert=ca_cert,
        ca_cert_key=ca_cert_key,
    )


@dataclass
class ClusterContext:
    config: ServerConfig


@dataclass
class GatewayContext:
    ip_list: List[str]
    username: str
    password: str
    bucket: str
    sgw_path: str
    tls: bool
    filename: Optional[str]


@dataclass
class CertContext:
    username: str
    password: str
    ip_address: Optional[str]
    external_ip_address: Optional[str]
    data_path: str
    filename: Optional[str]
    domain_name: Optional[str]
    alt_names: Optional[List[str]]
    host_cert: bool
    key_file: Optional[str]
    cert_file: Optional[str]
    base64: bool
    ca_cert: Optional[str]
    ca_cert_key: Optional[str]


@app.callback()
def main_callback(
    debug: Annotated[bool, typer.Option("--debug", help="Debug output")] = False,
    verbose: Annotated[bool, typer.Option("--verbose", help="Verbose output")] = False,
) -> None:
    _setup_logging(debug or verbose)


@cluster_app.callback()
def cluster_callback(
    ctx: typer.Context,
    name: Annotated[str, typer.Option("-n", "--name", help="Cluster name")] = "cbserver",
    ip_address: Annotated[
        Optional[str],
        typer.Option("-l", "--ip-address", help="Node IP address"),
    ] = None,
    rally_ip_address: Annotated[
        Optional[str],
        typer.Option("-r", "--rally-ip-address", help="Rally node IP address"),
    ] = None,
    external_ip_address: Annotated[
        Optional[str],
        typer.Option("-e", "--external-ip-address", help="External IP address"),
    ] = None,
    services: Annotated[
        str,
        typer.Option("-s", "--services", help="Comma-separated service list"),
    ] = "data,index,query",
    username: Annotated[str, typer.Option("-u", "--username")] = "Administrator",
    password: Annotated[str, typer.Option("-p", "--password")] = "password",
    index_mem: Annotated[
        str,
        typer.Option("-i", "--index-mem", help="Index memory option (default or memopt)"),
    ] = "default",
    server_group: Annotated[
        str,
        typer.Option("-g", "--server-group", help="Server group name"),
    ] = "group-1",
    data_path: Annotated[
        str,
        typer.Option("-D", "--data-path", help="Couchbase data path"),
    ] = "/opt/couchbase/var/lib/couchbase/data",
    community: Annotated[
        bool,
        typer.Option("-C", "--community", help="Community edition"),
    ] = False,
    private_key: Annotated[
        Optional[str],
        typer.Option("-K", "--private-key", help="Private key path"),
    ] = None,
    options: Annotated[
        Optional[str],
        typer.Option("-o", "--options", help="Comma-separated extra options"),
    ] = None,
    ca_cert: Annotated[
        Optional[str],
        typer.Option("--ca-cert", help="PEM-formatted cluster CA certificate"),
    ] = None,
    ca_cert_key: Annotated[
        Optional[str],
        typer.Option("--ca-cert-key", help="PEM-formatted cluster CA private key"),
    ] = None,
) -> None:
    ctx.obj = ClusterContext(
        config=_build_server_config(
            name,
            ip_address,
            rally_ip_address,
            external_ip_address,
            services,
            username,
            password,
            index_mem,
            server_group,
            data_path,
            community,
            private_key,
            options,
            ca_cert,
            ca_cert_key,
        )
    )


def _couchbase_server(ctx: typer.Context) -> CouchbaseServer:
    cluster_ctx: ClusterContext = ctx.obj
    return CouchbaseServer(cluster_ctx.config)


@cluster_app.command("create")
def cluster_create(ctx: typer.Context) -> None:
    config: ServerConfig = ctx.obj.config
    cbs = _couchbase_server(ctx)
    logger.info(f"Creating cluster {config.name}")
    cbs.create_cluster()


@cluster_app.command("add")
def cluster_add(ctx: typer.Context) -> None:
    cbs = _couchbase_server(ctx)
    logger.info(f"Adding node to cluster")
    cbs.add_node()


@cluster_app.command("update")
def cluster_update(ctx: typer.Context) -> None:
    config: ServerConfig = ctx.obj.config
    if not config.external_ip_address:
        raise typer.BadParameter("--external-ip-address is required for cluster update")
    cbs = _couchbase_server(ctx)
    logger.info(f"Updating external IP on node {config.ip_address}")
    cbs.update_external_ip()


@cluster_app.command("rebalance")
def cluster_rebalance(ctx: typer.Context) -> None:
    config: ServerConfig = ctx.obj.config
    cbs = _couchbase_server(ctx)
    logger.info(f"Balancing cluster {config.name}")
    cbs.rebalance()


@cluster_app.command("ca_cert")
def cluster_ca_cert(ctx: typer.Context) -> None:
    config: ServerConfig = ctx.obj.config
    cbs = _couchbase_server(ctx)
    logger.info(f"CA setup actions on {config.name}")
    cbs.cluster_ca_setup()


@cluster_app.command("node_cert")
def cluster_node_cert(ctx: typer.Context) -> None:
    config: ServerConfig = ctx.obj.config
    cbs = _couchbase_server(ctx)
    logger.info(f"Node certificate actions on {config.name}")
    cbs.node_cert_setup()


@cluster_app.command("cert_auth")
def cluster_cert_auth(ctx: typer.Context) -> None:
    config: ServerConfig = ctx.obj.config
    cbs = _couchbase_server(ctx)
    logger.info(f"Cert auth setup on {config.name}")
    cbs.cluster_cert_auth_setup()


@cluster_app.command("wait")
def cluster_wait(ctx: typer.Context) -> None:
    config: ServerConfig = ctx.obj.config
    cbs = _couchbase_server(ctx)
    logger.info(f"Waiting for cluster availability {config.name}")
    cbs.cluster_wait()


@gateway_app.callback()
def gateway_callback(
    ctx: typer.Context,
    ip_list: Annotated[
        str,
        typer.Option("-l", "--ip-list", help="Comma-separated IP list"),
    ] = "127.0.0.1",
    username: Annotated[str, typer.Option("-u", "--username")] = "Administrator",
    password: Annotated[str, typer.Option("-p", "--password")] = "password",
    bucket: Annotated[str, typer.Option("-b", "--bucket")] = "default",
    sgw_path: Annotated[
        str,
        typer.Option("-S", "--sgw-path", help="Sync Gateway root path"),
    ] = "/home/sync_gateway",
    tls: Annotated[bool, typer.Option("-T", "--tls", help="Use TLS")] = False,
    filename: Annotated[
        Optional[str],
        typer.Option("-f", "--filename", help="Destination config file"),
    ] = None,
) -> None:
    ctx.obj = GatewayContext(
        ip_list=_parse_csv(ip_list),
        username=username,
        password=password,
        bucket=bucket,
        sgw_path=sgw_path,
        tls=tls,
        filename=filename,
    )


def _sync_gateway(ctx: typer.Context) -> SyncGateway:
    gateway_ctx: GatewayContext = ctx.obj
    gc = GatewayConfig(
        gateway_ctx.ip_list,
        gateway_ctx.username,
        gateway_ctx.password,
        gateway_ctx.bucket,
        gateway_ctx.sgw_path,
        use_ssl=gateway_ctx.tls,
    )
    return SyncGateway(gc)


@gateway_app.command("configure")
def gateway_configure(ctx: typer.Context) -> None:
    gateway_ctx: GatewayContext = ctx.obj
    sgw = _sync_gateway(ctx)
    if not gateway_ctx.filename:
        logger.info("Configuring Sync Gateway node")
        sgw.configure()
    else:
        sgw.prepare(dest=gateway_ctx.filename)


@gateway_app.command("wait")
def gateway_wait(ctx: typer.Context) -> None:
    sgw = _sync_gateway(ctx)
    logger.info("Waiting for Sync Gateway node")
    sgw.gateway_wait()


@cert_app.callback()
def cert_callback(
    ctx: typer.Context,
    username: Annotated[str, typer.Option("-u", "--username")] = "Administrator",
    password: Annotated[str, typer.Option("-p", "--password")] = "password",
    ip_address: Annotated[
        Optional[str],
        typer.Option("-l", "--ip-address", help="Node IP address"),
    ] = None,
    external_ip_address: Annotated[
        Optional[str],
        typer.Option("-e", "--external-ip-address", help="External IP address"),
    ] = None,
    data_path: Annotated[
        str,
        typer.Option("-D", "--data-path", help="Output directory for CA files"),
    ] = "/opt/couchbase/var/lib/couchbase/data",
    filename: Annotated[
        Optional[str],
        typer.Option("-f", "--filename", help="Output file name"),
    ] = None,
    domain_name: Annotated[
        Optional[str],
        typer.Option("-d", "--domain", help="Certificate domain name"),
    ] = None,
    alt_names: Annotated[
        Optional[List[str]],
        typer.Option("-A", "--alt-names", help="Certificate alternate names"),
    ] = None,
    host_cert: Annotated[
        bool,
        typer.Option("-H", "--host-cert", help="Create hostname certificate"),
    ] = False,
    key_file: Annotated[
        Optional[str],
        typer.Option("-k", "--key-file", help="Private key file"),
    ] = None,
    cert_file: Annotated[
        Optional[str],
        typer.Option("-c", "--cert-file", help="Certificate file"),
    ] = None,
    base64: Annotated[
        bool,
        typer.Option("--base64", help="Output CA as base64"),
    ] = False,
    ca_cert: Annotated[
        Optional[str],
        typer.Option("--ca-cert", help="PEM-formatted cluster CA certificate"),
    ] = None,
    ca_cert_key: Annotated[
        Optional[str],
        typer.Option("--ca-cert-key", help="PEM-formatted cluster CA private key"),
    ] = None,
) -> None:
    ctx.obj = CertContext(
        username=username,
        password=password,
        ip_address=ip_address,
        external_ip_address=external_ip_address,
        data_path=data_path,
        filename=filename,
        domain_name=domain_name,
        alt_names=alt_names,
        host_cert=host_cert,
        key_file=key_file,
        cert_file=cert_file,
        base64=base64,
        ca_cert=ca_cert,
        ca_cert_key=ca_cert_key,
    )


@cert_app.command("key")
def cert_key(ctx: typer.Context) -> None:
    cert_ctx: CertContext = ctx.obj
    filename = cert_ctx.filename or "privkey.pem"
    CertMgr().private_key(filename)


@cert_app.command("create")
def cert_create(ctx: typer.Context) -> None:
    cert_ctx: CertContext = ctx.obj
    filename = cert_ctx.filename or "cert.pem"
    key_file = cert_ctx.key_file or "privkey.pem"
    if cert_ctx.host_cert:
        CertMgr().certificate_hostname(
            filename,
            key_file,
            cert_ctx.domain_name,
            cert_ctx.alt_names,
        )
    else:
        CertMgr().certificate_basic(filename, key_file)


@cert_app.command("user")
def cert_user(ctx: typer.Context) -> None:
    cert_ctx: CertContext = ctx.obj
    CertMgr().certificate_user(
        cert_ctx.cert_file,
        cert_ctx.key_file,
        cert_ctx.password,
        cert_ctx.username,
    )


@cert_app.command("ca")
def cert_ca(ctx: typer.Context) -> None:
    cert_ctx: CertContext = ctx.obj
    if cert_ctx.base64:
        key_encoded, cert_encoded = CertMgr().certificate_ca_base64()
        print("---- Begin Certificate Key ----")
        print(key_encoded)
        print("---- End Certificate Key ----")
        print("---- Begin Certificate ----")
        print(cert_encoded)
        print("---- End Certificate ----")
    else:
        key_file = os.path.join(cert_ctx.data_path, "ca.key")
        cert_file = os.path.join(cert_ctx.data_path, "ca.crt")
        CertMgr().certificate_ca_files(key_file, cert_file)


def _cert_server(cert_ctx: CertContext) -> CouchbaseServer:
    resolved_ip = _resolve_ip_address(cert_ctx.ip_address)
    config = ServerConfig(
        name="cbserver",
        ip_address=resolved_ip,
        rally_ip_address=resolved_ip,
        external_ip_address=cert_ctx.external_ip_address,
        services=["data"],
        username=cert_ctx.username,
        password=cert_ctx.password,
        data_path=cert_ctx.data_path,
        ca_cert=cert_ctx.ca_cert,
        ca_cert_key=cert_ctx.ca_cert_key,
    )
    return CouchbaseServer(config)


@cert_app.command("cluster-ca")
def cert_cluster_ca(ctx: typer.Context) -> None:
    cert_ctx: CertContext = ctx.obj
    cbs = _cert_server(cert_ctx)
    logger.info(f"Updating cluster CA on {cbs.ip_address}")
    cbs.cluster_ca_update()


@cert_app.command("node-cert")
def cert_node_cert(ctx: typer.Context) -> None:
    cert_ctx: CertContext = ctx.obj
    cbs = _cert_server(cert_ctx)
    logger.info(f"Updating node certificate on {cbs.ip_address}")
    cbs.node_cert_update()


def main(args: Optional[List[str]] = None) -> None:
    argv = args if args is not None else sys.argv
    try:
        app(args=argv[1:], prog_name=os.path.basename(argv[0]))
    except SystemExit as exc:
        raise SystemExit(exc.code) from None
