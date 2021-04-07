import json
import logging
import random
from time import sleep
from typing import List, Optional, Dict
import socks

import requests
from bs4 import BeautifulSoup


def from_txt_to_list(txt_path: str) -> List[str]:
    """
    Get a list of string from a txt, one element per line
    :param txt_path: path to txt file
    :return: List of str, one per file row
    """
    rows = []
    with open(txt_path) as open_txt:
        for line in open_txt:
            if line.strip():
                rows.append(line.strip())
    return rows


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
        logging.warning(f"Changed server, now using '{self.servers[self.server_number]}'")

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


class ElementScraper:
    url: str
    soup: BeautifulSoup
    save_path: str = ''
    proxy_server: Optional[ProxyServer] = None
    was_cached: bool = False
    headers: dict = {"User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:87.0) Gecko/20100101 Firefox/87.0"}

    def __init__(self, url: str, proxy_server: Optional[ProxyServer] = None):
        self.url = url
        self.proxy_server = proxy_server

    def update_proxy_get_response(self) -> requests.Response:
        """
        Update proxy server coordinates, and make call to url
        :return: response to url get http request
        """
        self.proxy_server.update_server_used()
        requests.Session().cache.delete_url(self.url)
        return self.http_call(self.proxy_server.get_proxy())

    def get(self):
        """
        Retrieve the experience HTML code and input it
        for further processing
        """
        proxy = self.proxy_server.get_proxy() if self.proxy_server else None
        try:
            res = self.http_call(proxy)
            res.raise_for_status()
        except (requests.exceptions.ConnectionError, socks.SOCKS5AuthError):
            logging.error("ConnectionError or SOCKS5AuthError")
            res = self.update_proxy_get_response()
        if res.text.find("IP address has been blocked") != -1 and proxy is not None:
            self.update_proxy_get_response()
        self.was_cached = res.from_cache
        self.soup = BeautifulSoup(res.content, 'html.parser')

    def http_call(self, proxy) -> requests.Response:
        raise NotImplementedError("method http_call must be implemented")

    def extract_data(self):
        raise NotImplementedError("method extract_data must be implemented")

    def save(self):
        raise NotImplementedError("method save must be implemented")


class ListScraper:
    raise_exceptions: bool
    seed: int = 666
    save_folder: str = ""
    urls_to_download: Dict[str, ElementScraper] = {}
    base_url: str = ""
    min_wait: int = 10
    max_wait: int = 30
    proxy_server: Optional[Dict[str, str]]

    def __init__(self, raise_exceptions: bool = False, proxy_server: Optional[ProxyServer] = None):
        self.raise_exceptions = raise_exceptions
        self.proxy_server = proxy_server

    def download(self, wait: bool = False):
        """
        Download all the urls contained in urls_to_be_downloaded
        Wait for a random interval between a range, if needed.
        Never wait when the url to download was already cached.

        :param wait: Whether it should wait a random number of seconds (in a range) between downloads
        """
        urls_downloaded = 0
        urls_failed = 0
        logging.info(f"A total of {len(self.urls_to_download)} links will be attempted to download")
        for i, scraper in enumerate(self.urls_to_download.values()):
            try:
                logging.info(f"Downloading {scraper.url}...")
                scraper.get()
                scraper.extract_data()
                scraper.save()
                urls_downloaded += 1
                logging.info(f"success. So far {urls_downloaded} pages downloaded correctly.")
            except Exception as e:
                if self.raise_exceptions:
                    raise
                logging.exception('failed:')
                with open(f'exp_links/failed_urls_{type(e).__name__}.txt', 'a') as open_txt:
                    open_txt.write(scraper.url)
                    open_txt.write('\n')
                urls_failed += 1
                logging.error(f"So far {urls_failed} errors.")
            if wait and not scraper.was_cached:
                sleep(random.randint(self.min_wait, self.max_wait))

    def update_download_list(self):
        raise NotImplementedError
