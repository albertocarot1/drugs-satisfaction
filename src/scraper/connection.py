import json
import logging
import random
from typing import List

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class ProxyServer:
    servers: List[str]
    username: str
    password: str
    server_number: int
    server_in_use: str

    def __init__(self, cred_file):
        """
        Use credentials file to setup proxy.
        Initialise servers in a random order,
        :param cred_file:
        """
        with open(cred_file) as open_json:
            credentials = json.load(open_json)
        self.username = credentials["username"]
        self.password = credentials["password"]
        self.servers = credentials["servers"]
        assert len(self.servers) > 0
        random.shuffle(self.servers)
        self.server_number = 0
        self.server_in_use = self.servers[self.server_number]

    def update_server_used(self):
        """
        Change the server in use with the next one in `servers` list
        """
        if self.server_number < len(self.servers) - 1:
            self.server_number += 1
        else:
            self.server_number = 0
        self.server_in_use = self.servers[self.server_number]
        logger.warning(f"Changed server, now using '{self.servers[self.server_number]}'")

    def get_proxy(self):
        """
        Return proxy credentials to use to make socks calls though requests
        :return: dict with credenials and server for http and https
        """
        proxy_string = f"socks5://{self.username}:{self.password}@{self.server_in_use}:1080"
        return {
            'http': proxy_string,
            'https': proxy_string
        }
