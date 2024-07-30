# host-prep-lib 1.0.53

Automation for preparing a host to run Couchbase software.

Note: This package is not officially supported by Couchbase.

## Quick Start

Install the software bundle for Couchbase Server and all prerequisites
```
# bundlemgr -b CBS
```

Configure a Couchbase Server cluster with three nodes
```
swmgr cluster -n cbdb -l 192.168.1.5,192.168.1.6,192.168.1.7
```
