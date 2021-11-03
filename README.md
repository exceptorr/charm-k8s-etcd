# charm-k8s-etcd

## Description

Etcd is a highly available distributed key value store that provides a reliable
way to store data across a cluster of machines. Etcd gracefully handles master
elections during network partitions and will tolerate machine failure,
including the master.

## Usage

    microk8s.enable storage dns
    juju bootstrap microk8s micro
    charmcraft build
    juju deploy ./charm-k8s-etcd.charm --resource etcd-image=gcr.io/etcd-development/etcd:v3.5.0 etcd -n 2

## Configuration
Currently, this charm has only two config options:

- loglevel: controlling the etcd's log level verbosity. Defaults to info.
- metrics: Set level of detail for exported Prometheus metrics.

## Accessing the cluster

    ETCD_VER=v3.5.0
    DOWNLOAD_URL=https://github.com/etcd-io/etcd/releases/download
    
    rm -f /tmp/etcd-${ETCD_VER}-linux-amd64.tar.gz
    rm -rf /tmp/etcd-download-test && mkdir -p /tmp/etcd-download-test
    
    curl -L ${DOWNLOAD_URL}/${ETCD_VER}/etcd-${ETCD_VER}-linux-amd64.tar.gz -o /tmp/etcd-${ETCD_VER}-linux-amd64.tar.gz
    tar xzvf /tmp/etcd-${ETCD_VER}-linux-amd64.tar.gz -C /tmp/etcd-download-test --strip-components=1
    rm -f /tmp/etcd-${ETCD_VER}-linux-amd64.tar.gz

    # get accessible unit ip addresses
    ENDPOINTS=(); for endpoint in $(juju run --application etcd 'network-get etcd-cluster --bind-address=true' | grep 10.1); do ENDPOINTS+=($endpoint); done; ENDPOINT_LIST=$(printf ",http://%s:2379" "${ENDPOINTS[@]}"); ENDPOINT_LIST=${ENDPOINT_LIST:1};
    echo $ENDPOINT_LIST
    /tmp/etcd-download-test/etcdctl --endpoints $ENDPOINT_LIST endpoint status -w table

## Developing

Create and activate a virtualenv with the development requirements:

    virtualenv -p python3 venv
    source venv/bin/activate
    pip install -r requirements-dev.txt

## Testing

The Python operator framework includes a very nice harness for testing
operator behaviour without full deployment. Just `run_tests`:

    ./run_tests
