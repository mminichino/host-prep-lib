# host-prep-lib

Automation for preparing a host to run Couchbase software.

Note: This package is not officially supported by Couchbase.

## Quick Start

Install the software bundle for Couchbase Server and all prerequisites:

```
bundlemgr -b CBS
```

## swmgr

`swmgr` manages Couchbase Server clusters, Sync Gateway, and certificates. Run each command on the target host. Global options:

```
swmgr [--debug] [--verbose] COMMAND ...
```

### Cluster

Cluster options are shared by all `cluster` subcommands:

```
swmgr cluster [OPTIONS] COMMAND

Options:
  -n, --name                 Cluster name (default: cbserver)
  -l, --ip-address           Node IP address (default: auto-detected)
  -r, --rally-ip-address     Rally node IP address (default: node IP)
  -e, --external-ip-address  External IP address for alternate addressing
  -s, --services             Comma-separated services (default: data,index,query)
  -u, --username             Cluster username (default: Administrator)
  -p, --password             Cluster password (default: password)
  -i, --index-mem            Index memory option: default or memopt (default: default)
  -g, --server-group         Server group name (default: group-1)
  -D, --data-path            Couchbase data path
  -C, --community            Community edition
  -K, --private-key          Private key path
  -o, --options              Comma-separated extra options (e.g. memopt)
```

Commands:

| Command     | Description |
|-------------|-------------|
| `create`    | Initialize a new cluster on this node |
| `add`       | Add this node to an existing cluster |
| `update`    | Set or update the external IP on this node (requires `-e`) |
| `rebalance` | Rebalance the cluster |
| `ca_cert`   | Load the cluster certificate authority |
| `node_cert` | Generate and load the node certificate |
| `cert_auth` | Enable certificate-based client authentication |
| `wait`      | Wait for the cluster to become available |

Create a three-node cluster (run on each node with the appropriate IP and rally address):

```
# Node 1 (rally node)
swmgr cluster -n cbdb -l 192.168.1.5 create

# Node 2
swmgr cluster -n cbdb -l 192.168.1.6 -r 192.168.1.5 add

# Node 3
swmgr cluster -n cbdb -l 192.168.1.7 -r 192.168.1.5 add

# Rebalance from the rally node
swmgr cluster -r 192.168.1.5 rebalance
```

Create or add a node with an external IP address. The external address is configured as an alternate address, and the node certificate is updated to include it as a subject alternative name when a CA private key is available:

```
swmgr cluster -l 192.168.1.6 -r 192.168.1.5 -e 1.2.3.4 -u user -p password add
```

Update the external IP on an existing node:

```
swmgr cluster -u user -p password -e 1.2.3.4 update
```

### Certificate

Certificate options are shared by all `cert` subcommands:

```
swmgr cert [OPTIONS] COMMAND

Options:
  -u, --username   Cluster username (default: Administrator)
  -p, --password   Cluster password (default: password)
  -l, --ip-address Node IP address (default: auto-detected)
  -D, --data-path  Output directory for CA files
  -f, --filename   Output file name
  -d, --domain     Certificate domain name
  -A, --alt-names  Certificate alternate names
  -H, --host-cert  Create hostname certificate
  -k, --key-file   Private key file
  -c, --cert-file  Certificate file
  --base64         Output CA as base64
```

Commands:

| Command  | Description |
|----------|-------------|
| `key`    | Generate a private key |
| `create` | Generate a certificate |
| `user`   | Generate a client certificate (PKCS12) |
| `ca`     | Generate a certificate authority |
| `update` | Regenerate and reload the node certificate using the cluster trusted root CA |

Update the node certificate on the local node. The trusted root CA is fetched from `GET /pools/default/trustedCAs`. The new certificate includes the internal IP and the external IP (if configured) as subject alternative names:

```
swmgr cert -u user -p password update
```

### Gateway

```
swmgr gateway [OPTIONS] COMMAND

Options:
  -l, --ip-list   Comma-separated Couchbase Server IP list (default: 127.0.0.1)
  -u, --username  Cluster username (default: Administrator)
  -p, --password  Cluster password (default: password)
  -b, --bucket    Bucket name (default: default)
  -S, --sgw-path  Sync Gateway root path (default: /home/sync_gateway)
  -T, --tls       Use TLS
  -f, --filename  Destination config file
```

Commands:

| Command     | Description |
|-------------|-------------|
| `configure` | Configure Sync Gateway on this host |
| `wait`      | Wait for Sync Gateway to become available |

Example:

```
swmgr gateway -l 192.168.1.5,192.168.1.6,192.168.1.7 configure
```
