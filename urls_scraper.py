import logging
from typing import List, Optional

import requests
import requests_cache

from utils import ListScraper, ElementScraper, ProxyServer

requests_cache.install_cache('erowid_cache')
logging.basicConfig(level=logging.INFO)

class UrlListScraper(ElementScraper):


    def __init__(self, url: str, proxy_server: Optional[ProxyServer] = None):
        super().__init__(url, proxy_server)


    def get(self):
        super().get()

    def http_call(self, proxy):
        pass

    def extract_data(self):


    def save(self):
        raise NotImplementedError("method save must be implemented")



class ErowidUrlsScraper(ListScraper):
    # Scan through search result pages to collect urls to download.
    base_url: str = "https://www.erowid.org/experiences/exp.cgi"
    save_folder: str = "exp_links"
    start: int = 0
    max_step: int = 100
    base_params: dict = {'ShowViews':0, 'Cellar':0, 'Start':start, 'Max':max_step}
    final_start: int = 36900

    def update_download_list(self, file: str = ''):
        for i in range(0, self.final_start, )
            self.urls_to_download





def main():
    erowid_scraper = ErowidUrlsScraper()
    proxy = ProxyServer("credentials.json")
    erowid_scraper.update_download_list()
    erowid_scraper.download(wait=True)


if __name__ == '__main__':
    main()