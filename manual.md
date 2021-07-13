```
# first

ETCD_NAME=infra0 ETCD_INITIAL_CLUSTER_TOKEN=token ETCD_LISTEN_CLIENT_URLS="http://0.0.0.0:2379" ETCD_ADVERTISE_CLIENT_URLS='http://10.211.55.7:2379' ETCD_LISTEN_PEER_URLS=http://10.211.55.7:2380 ETCD_INITIAL_CLUSTER="infra0=http://10.211.55.7:2380" ETCD_INITIAL_CLUSTER_STATE=new ETCD_INITIAL_ADVERTISE_PEER_URLS="http://10.211.55.7:2380" /tmp/etcd-download-test/etcd

# second

ubuntu@ubuntu:~/charm-k8s-etcd$ /tmp/etcd-download-test/etcdctl member add infra1 --peer-urls=http://10.211.55.8:2380
Member d33a83434be5a848 added to cluster  74de06e38ff30a0


ETCD_NAME=infra1 ETCD_INITIAL_CLUSTER_TOKEN=token ETCD_INITIAL_CLUSTER="infra0=http://10.211.55.7:2380,infra1=http://10.211.55.8:2380" ETCD_INITIAL_ADVERTISE_PEER_URLS="http://10.211.55.8:2380" ETCD_INITIAL_CLUSTER_STATE="existing" ETCD_LISTEN_CLIENT_URLS="http://0.0.0.0:2379" ETCD_ADVERTISE_CLIENT_URLS='http://10.211.55.8:2379' ETCD_LISTEN_PEER_URLS=http://10.211.55.8:2380 /tmp/etcd-download-test/etcd
```