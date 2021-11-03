#!/usr/bin/env python3
# Copyright 2021 ubuntu
# See LICENSE file for licensing details.
#
# Learn more at: https://juju.is/docs/sdk

"""Charm the service.

Refer to the following post for a quick-start guide that will help you
develop a new k8s charm using the Operator Framework:

    https://discourse.charmhub.io/t/4208
"""

import logging
import secrets

from ops.framework import StoredState
from ops.main import main
from ops.model import (
    ActiveStatus, WaitingStatus, BlockedStatus,
    MaintenanceStatus
)
from ops.charm import (
    CharmBase,
)
from ops.pebble import ChangeError
# from cluster import EtcdCluster
from client import EtcdClient

logger = logging.getLogger(__name__)

class CharmEtcd(CharmBase):

    _stored = StoredState()
    __CLUSTER_NOT_INITIALIZED = '0'
    __CLUSTER_INITIALIZED = '1'
    __CLIENT_PORT = 2379
    __CLUSTER_PORT = 2380

    __PEBBLE_SERVICE_NAME = 'etcd'
    __PEER_RELATION_NAME = 'etcd-cluster'
    __INGRESS_ADDR_PEER_REL_DATA_KEY = 'ingress-address'
    __LEADER_IP_REL_DATA_KEY = 'leader-address'
    __CLUSTER_INITIALIZED_REL_DATA_KEY = 'cluster-initialized'
    __BOOTSTRAP_TOKEN_REL_DATA_KEY = 'bootstrap-token'

    BOOTSTRAP_NEW = 'new'
    BOOTSTRAP_EXISTING = 'existing'

    def __init__(self, *args):
        super().__init__(*args)
        events = [
            [self.on.etcd_pebble_ready, self._on_etcd_pebble_ready],
            [self.on.config_changed, self._on_config_or_peer_changed],
            [self.on.etcd_cluster_relation_created, self._on_cluster_created],
            [self.on.etcd_cluster_relation_joined, self._on_cluster_joined],
            [self.on.etcd_cluster_relation_changed, self._on_config_or_peer_changed]
        ]
        for event, handler in events:
            self.framework.observe(event, handler)

        self._stored.set_default(
            bootstrap_token=None,
            bootstrap_mode=None,
            is_registered=False
        )

    @property
    def peer_relation(self):
        return self.framework.model.get_relation(self.__PEER_RELATION_NAME)

    @property
    def app(self):
        return self.peer_relation.app

    @property
    def peer_databag(self):
        return self.peer_relation.data[self.app]

    @property
    def peer_unit_databag(self):
        return self.peer_relation.data[self.unit]

    @property
    def cluster_initialized(self):
        return self.peer_databag[self.__CLUSTER_INITIALIZED_REL_DATA_KEY] == self.__CLUSTER_INITIALIZED

    def _on_cluster_created(self, event):
        if not self.peer_unit_databag.get("registration_ip"):
            self.peer_unit_databag["registration_ip"] = self._get_pod_ip()

        if not self.model.unit.is_leader():
            logger.warning("not a leader, cannot bootstrap - will join existing")
            if not self._stored.bootstrap_mode:
                self._stored.bootstrap_mode = self.BOOTSTRAP_EXISTING
            return

        if not self._stored.bootstrap_token:
            token = secrets.token_hex(8)
            self._stored.bootstrap_token = token
            self._stored.bootstrap_mode = self.BOOTSTRAP_NEW
            self.peer_databag[
                self.__BOOTSTRAP_TOKEN_REL_DATA_KEY] = self._stored.bootstrap_token
            self.peer_databag[
                self.__LEADER_IP_REL_DATA_KEY] = self._get_pod_ip()
            self.peer_databag[self.__CLUSTER_INITIALIZED_REL_DATA_KEY] = self.__CLUSTER_NOT_INITIALIZED
            logger.error("Writing bootstrap token to leader local storage")

    def _on_cluster_joined(self, event):
        logger.warning('Cluster relation joined: %s' % str(event))
        is_leader = self.model.unit.is_leader()
        bootstrap_token = self.peer_databag.get(self.__BOOTSTRAP_TOKEN_REL_DATA_KEY)
        self.peer_unit_databag[self.__INGRESS_ADDR_PEER_REL_DATA_KEY] = self._get_pod_ip()
        logger.error(dict(self.peer_unit_databag))

        if not bootstrap_token:
            if not is_leader:
                logger.error('No bootstrap-token pushed by leader. Waiting')
                self.unit.status = WaitingStatus("Waiting a bootstrap token")
                event.defer()
        else:
            self._stored.bootstrap_token = bootstrap_token
            logger.error('got a token from relation: %s' % bootstrap_token)
            if not is_leader:
                # assume leader has been started already
                self.unit.status = WaitingStatus("Waiting for Etcd member registration")

    def _on_etcd_pebble_ready(self, event):
        logger.error("_on_etcd_pebble_ready")
        self._start_etcd(event.workload, enabled=False)
        logger.error("_on_etcd_pebble_ready: done")

    def register_new_member(self):
        logger.error("register-new-member")
        logger.error(self._get_pod_ip())
        logger.error(self.peer_databag[self.__LEADER_IP_REL_DATA_KEY])

        if self._stored.is_registered:
            logger.error("This pod has already been registered. Exiting")
            return True

        if self._get_pod_ip() == self.peer_databag[self.__LEADER_IP_REL_DATA_KEY]:
            # no need to register the leader within himself
            logger.error("skip self registration")
            return True

        self.unit.status = MaintenanceStatus("Waiting for member registration")
        client = EtcdClient(
            client_ip=self.peer_databag[self.__LEADER_IP_REL_DATA_KEY],
            client_port=self.__CLIENT_PORT,
            cluster_port=self.__CLUSTER_PORT
        )
        if client.ping():

            if client.add_new_member(self._get_pod_ip()):
                self._stored.is_registered = True
                return True
            else:
                self.unit.status = BlockedStatus("Registration failed. See logs")
                return False
        else:
            # Leader unit etcd API is not available
            self.unit.status = MaintenanceStatus(
                "Etcd leader not ready. Deferring registration")
            return False

    def _start_etcd(self, container, enabled=True):
        msg = "Restarting Etcd" if enabled else "Adding dummy Pebble layer"
        self.unit.status = MaintenanceStatus(msg)
        etcd_layer = self.generate_pebble_config(enabled)

        # Add initial Pebble config layer using the Pebble API
        container.add_layer("etcd", etcd_layer, combine=True)

        # Autostart any services that were defined with startup: enabled
        if not container.get_service('etcd').is_running():
            if enabled:
                logger.info('Autostarting etcd')
                try:
                    container.autostart()
                except Exception as e:
                    enabled = False
                    logger.error("Failed to start etcd container")
                    logger.error(e)
        else:
            # Stop and restart then
            try:
                container.stop(self.__PEBBLE_SERVICE_NAME)
            except ChangeError as e:
                logger.error("Failed to stop Pebble-running service:")
                logger.error(e.err)
            container.autostart()

        if enabled:
            is_leader = str(self.model.unit.is_leader())
            self.unit.status = ActiveStatus(
                "Unit is ready (bootstrap: {2}, leader: {0}, token: {1})".format(
                    is_leader, self._stored.bootstrap_token,
                    self._stored.bootstrap_mode
                )
            )

    def _get_pod_ip(self):
        return str(
            self.model.get_binding(self.peer_relation).network.bind_address
        )

    def get_etcd_environment(self):
        pod_ip = self._get_pod_ip()

        allowed_log_levels = [
            'debug', 'info', 'warn', 'error', 'panic', 'fatal'
        ]
        logging_level = self.model.config['loglevel'].lower()
        if logging_level not in allowed_log_levels:
            self.unit.status = BlockedStatus(
                "Invalid loglevel provided: %s" % logging_level
            )
            return

        pod_cluster_endpoint = "http://{0}:{1}".format(pod_ip, self.__CLUSTER_PORT)


        env = {
            "ETCD_LOG_LEVEL": logging_level,
            "ETCD_NAME": self.unit.name.replace('/', ''),
            "ETCD_LISTEN_CLIENT_URLS": "http://0.0.0.0:{0}".format(self.__CLIENT_PORT),
            "ETCD_ADVERTISE_CLIENT_URLS": "http://{0}:{1}".format(pod_ip, self.__CLIENT_PORT),
            "ETCD_LISTEN_PEER_URLS": pod_cluster_endpoint,
            "ETCD_INITIAL_ADVERTISE_PEER_URLS": pod_cluster_endpoint,
            "ETCD_INITIAL_CLUSTER_TOKEN": self._stored.bootstrap_token,
            "ETCD_INITIAL_CLUSTER_STATE": self._stored.bootstrap_mode,
        }

        if self.model.config['metrics'] in ['basic', 'extensive']:
            env['ETCD_METRICS'] = self.model.config['metrics']

        current_pod_only = False
        if self._stored.bootstrap_mode == self.BOOTSTRAP_NEW:
            current_pod_only = True

        logger.error("current pod: %s" % current_pod_only)
        env['ETCD_INITIAL_CLUSTER'] = ','.join(self._render_cluster_addresses(
            current_pod_only
        ))

        logger.error("generated env: %s" % env)
        return env

    def _on_config_or_peer_changed(self, event):
        logger.error("config-changed or peer invoked: %s" % event)
        # container = self.unit.get_container(self.__PEBBLE_SERVICE_NAME)
        # services = container.get_plan().to_dict().get('services', {})
        #
        # if not len(services):
        #     logger.info('no Pebble services defined yet')
        #     # No Pebble service defined yet, too early:
        #     return
        #
        # Get a reference the container attribute on the PebbleReadyEvent

        container = self.unit.get_container(self.__PEBBLE_SERVICE_NAME)
        # container = event.workload

        if self.cluster_initialized:
            # this cluster has been already initialized
            self._stored.bootstrap_token = self.peer_databag.get(self.__BOOTSTRAP_TOKEN_REL_DATA_KEY)
            if not self._stored.bootstrap_mode:
                self._stored.bootstrap_mode = self.BOOTSTRAP_EXISTING

        if not self._stored.bootstrap_token:
            logger.error("Leader not bootstrapped")
            self.unit.status = WaitingStatus("Waiting for leader bootstrap.")
        else:
            if not self.cluster_initialized:
                # This unit should initialize the cluster, run etcd immediately
                self.peer_databag[self.__CLUSTER_INITIALIZED_REL_DATA_KEY] = self.__CLUSTER_INITIALIZED
                self._stored.is_registered = True
                logger.error("Starting leader container")
                self._start_etcd(container)
            else:
                # This unit has to register itself as a peer member with leader unit.
                self.register_new_member() or event.defer()

                if len(self._render_cluster_addresses()) > 1:
                    logger.error("Staring peer container")
                    # some remote peers have connected - can run non-leader unit
                    self._start_etcd(container)
                else:
                    self.unit.status = WaitingStatus("Waiting for peers.")
                    logger.error("No peers connected")

    def generate_pebble_config(self, enabled=True):
        etcd_env = self.get_etcd_environment()
        if not etcd_env:
            raise RuntimeError("Error building etcd env")

        return {
                "summary": "etcd layer",
                "description": "pebble config layer for etcd",
                "services": {
                    self.__PEBBLE_SERVICE_NAME: {
                        "override": "replace",
                        "summary": "etcd",
                        "command": "/usr/local/bin/etcd",
                        "startup": "enabled" if enabled else "disabled",
                        "environment": etcd_env
                    }
                },
            }

    def _render_cluster_addresses(self, current_pod_only=False):
        """Get all ingress addresses shared by all peers over the relation.
        Including the current unit.
        """
        unit_data = dict()
        result = []
        relation = self.peer_relation

        my_ingress_address = self._get_pod_ip()
        if my_ingress_address is not None:
            unit_data[self.unit.name.replace('/', '')] = str(
                my_ingress_address
            )

        if not current_pod_only:
            for unit in relation.units:
                try:
                    unit_ingress_address = relation.data[unit][
                        self.__INGRESS_ADDR_PEER_REL_DATA_KEY]
                except KeyError:
                    # This unit hasn't shared its address yet.
                    # It's OK as there will be other hook executions
                    # later calling this again:
                    continue
                if unit_ingress_address is not None:
                    unit_data[unit.name.replace('/', '')] = str(
                        unit_ingress_address
                    )

        logging.debug('All unit ingress addresses: {}'.format(unit_data))

        for k, v in unit_data.items():
            result.append('{0}=http://{1}:{2}'.format(k, v, self.__CLUSTER_PORT))

        return result


if __name__ == "__main__":
    main(CharmEtcd)
