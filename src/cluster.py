import json

from ops.framework import Object, StoredState, ObjectEvents, EventBase, EventSource
from ops.model import Relation

class ClusterChanged(EventBase):
    """An event raised by EtcdCluster when cluster-wide settings change.
    """

class TokenAvailable(EventBase):
    """An event raised by EtcdCluster when leader generates a token
    """


class EtcdClusterEvents(ObjectEvents):
    cluster_changed = EventSource(ClusterChanged)
    token_available = EventSource(TokenAvailable)

import logging
logger = logging.getLogger(__name__)


class EtcdCluster(Object):

    on = EtcdClusterEvents()
    _stored = StoredState()

    def __init__(self, charm, relation_name):
        super().__init__(charm, relation_name)
        self._relation_name = relation_name

        self.framework.observe(charm.on[relation_name].relation_created,
                               self._on_created)
        self.framework.observe(charm.on[relation_name].relation_changed,
                               self._on_changed)

    def _on_created(self, event):
        self._notify_cluster_changed()

    def _on_changed(self, event):
        self._notify_cluster_changed()

    @property
    def etcd(self) -> Relation:
        """The relation associated with this interface"""
        return self.framework.model.get_relation(self._relation_name)

    def _notify_cluster_changed(self):
        if self.bootstrap_token:
            logger.debug(
                "Bootstrap token provided by leader, emitting TokenAvailableEvent event"
            )
            self.on.token_available.emit()
        self.on.cluster_changed.emit()

    @property
    def bootstrap_token(self) -> str:
        """Current bootstrap token provided via the peer relation application databag"""
        x = self.etcd.data[self.etcd.app].get("bootstrap-token")
        logger.debug("Reading bootstrap-token: got %s" % x)
        return x

    @property
    def is_established(self):
        return self.etcd is not None
