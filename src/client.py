import requests
import json
import logging
import time

from requests.exceptions import RequestException

logger = logging.getLogger(__name__)


class EtcdClient(object):

    def __init__(self, client_ip, client_port, cluster_port):
        self.client_ip = client_ip
        self.client_port = client_port
        self.protocol = 'http'
        self.endpoint_stub = 'http://{0}' + ':{0}'.format(cluster_port)
        logger.error("Initialized Etcd client: %s" % self.base_url)

    @property
    def base_url(self):
        return '{0}://{1}:{2}'.format(
            self.protocol, self.client_ip, self.client_port
        )

    def endpoint(self, url):
        if url.startswith('/'):
            url = url[1:]
        ep = '{0}/{1}'.format(self.base_url, url)
        logger.error(ep)
        return ep

    def ping(self):
        try:
            logger.error(requests.get(self.endpoint('version'), timeout=3).text)
            return True
        except RequestException as e:
            logger.error("ping probe failed: %s" % e)
            return False

    def get_member_list(self):
        r = requests.post(
            self.endpoint('v3/cluster/member/list')
        )
        logger.error(r.text)

        return r.json()['members']

    def is_ip_registered(self, ip):
        members = self.get_member_list()
        stub = self.endpoint_stub.format(ip)
        for member in members:
            member_peers = member['peerURLs']
            for peer in member_peers:
                if peer == stub:
                    logger.error("Found registered IP %s" % ip)
                    return True
        logger.error("Looks like IP %s is not registered as ETCD peer" % ip)
        return False

    def add_new_member(self, peer_ip):
        logger.error("add new member with ip: %s" % peer_ip)
        if self.is_ip_registered(peer_ip):
            return True

        payload = {
            'peerURLs': [self.endpoint_stub.format(peer_ip)]
        }

        timeouts = [x * x for x in range(5, 10)]

        for i, timeout in enumerate(timeouts):
            logging.error("Registration attempt {0} from {1}".format(i, len(timeouts)))
            req = requests.post(
                self.endpoint('v3/cluster/member/add'),
                data=json.dumps(payload)
            )

            logging.error("RAW data from Etcd:")
            logging.error(req.text)

            response = req.json()
            if response.get("error"):
                logging.error("Error registering new Etcd member: %s" % response.get("error"))
                logging.error("Waiting for {0} sec...".format(timeout))
                time.sleep(timeout)
            else:
                # no error - exit
                logging.error("New member registered")
                return True

        logging.error("add-new-member done")
        return False