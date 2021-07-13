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
    juju deploy ./charm-k8s-etcd.charm --resource etcd-image=gcr.io/etcd-development/etcd:v3.5.0 # quay.io/coreos/etcd etcd
    juju upgrade-charm etcd --path=./charm-k8s-etcd.charm --force-units

## Developing

Create and activate a virtualenv with the development requirements:

    virtualenv -p python3 venv
    source venv/bin/activate
    pip install -r requirements-dev.txt

## Testing

The Python operator framework includes a very nice harness for testing
operator behaviour without full deployment. Just `run_tests`:

    ./run_tests
