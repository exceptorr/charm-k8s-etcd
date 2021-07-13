# Thoughts and feedback

- It would be nice to have some major IDE (PyCharm, VS Code etc) integration tips or suggestions. 
- How can I get a pod IP address?
  - Solved: self.model.get_binding(relation).network.bind_address
  - However, it will be nice to have it somewhere accessible in a unit databag. Currently, it has ```{'egress-subnets': '10.152.183.94/32', 'ingress-address': '10.152.183.94', 'private-address': '10.152.183.94'}``` only.
- How can I ssh to the workload container? juju ssh unit/0 leads me to the container agent
  - juju ssh --container etcd unit/0
- Juju shows unnecessary (?) log messages
  
        unit-etcd-1: 15:36:14 DEBUG jujuc running hook tool "juju-log" for etcd/1-etcd-pebble-ready-384624076606093122
        unit-etcd-1: 15:36:14 DEBUG unit.etcd/1.juju-log NOT A LEADER
- How can one share info between the units, assuming peer relation hasn't been built yet?
https://juju.is/docs/t/leadership-howtos/1123 suggests a `leader_set` & `leader_get` approach, but
I wasn't able to find more info about those: https://ops.readthedocs.io/en/latest/search.html?q=leader_set&check_keywords=yes&area=default
  - I've opted in to use app-wide databag https://juju.is/docs/sdk/relations "Application leaders can read and write their application buckets (e.g. `event.relation.data[self.app])`"

- 
- There is no native way to build a process, which runs sequentially on each unit (e.g not at all units in parallel). 
- ~~Synchronization process took a lot of time to implement correctly. Would be nice to have some best-practice guidance in the docs.~~

