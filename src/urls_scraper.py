import logging
import os
from copy import deepcopy
from typing import List, Optional

import requests
import requests_cache

from utils import ListScraper, ElementScraper, ProxyServer

requests_cache.install_cache('data/erowid_cache')
logging.basicConfig(level=logging.INFO)


class UrlListScraper(ElementScraper):
    params: dict
    experiences_urls: List[str] = None
    base_url: str = "https://www.erowid.org/experiences/"

    def __init__(self, url: str, params: dict, proxy_server: Optional[ProxyServer] = None):
        super().__init__(url, proxy_server)
        self.params = params
        self.exp_list_id = f"{params['Start']}_{params['Start'] + params['Max']}"
        self.experiences_urls = []

    def http_call(self, proxy):
        """
        Make the call to the urls list
        :param proxy: proxy server to use for the call
        :return: requests response
        """
        return requests.get(self.url,
                            proxies=proxy,
                            headers=self.headers,
                            allow_redirects=False,
                            params=self.params)

    def extract_data(self):
        """
        Extract all the experiences urls found in the page, and append them to the list
        of urls.
        """
        exp_list_table_rows = self.soup.find_all(class_="exp-list-table")[0].find_all('tr')
        for row in exp_list_table_rows:
            a_tag = row.find_all('a')
            if a_tag:
                exp_end_url = a_tag[0].attrs['href'].strip()
                exp_url = self.base_url + exp_end_url
                self.experiences_urls.append(exp_url)

    def save(self):
        """
        Save extracted urls in the file located in `save_path`.
        """
        with open(self.save_path, 'w') as open_txt:
            for el in self.experiences_urls:
                open_txt.write(el)
                open_txt.write('\n')


class ErowidUrlsScraper(ListScraper):
    # Scan through search result pages to collect urls to download.
    base_url: str = "https://www.erowid.org/experiences/exp.cgi"
    save_folder: str = "data/exp_links"
    start: int = 0
    max_step: int = 1000
    base_params: dict = {'ShowViews': 0, 'Cellar': 1, 'Start': start, 'Max': max_step}
    final_start: int = 39300

    def update_download_list(self, file: str = ''):
        """
        Update the list of URLs to download.

        :return:
        """
        urls_scrapers = []
        for i in range(self.start, self.final_start, self.max_step):
            params = deepcopy(self.base_params)
            params['Start'] = i
            urls_scraper = UrlListScraper(self.base_url, params, proxy_server=self.proxy_server)
            candidate_path = os.path.join(self.save_folder, f"{urls_scraper.exp_list_id}.txt")
            if os.path.isfile(candidate_path):
                logging.debug(f"List of urls {urls_scraper.exp_list_id} already downloaded")
            else:
                urls_scraper.save_path = candidate_path
                self.urls_to_download[urls_scraper.exp_list_id] = urls_scraper


def main():
    proxy = ProxyServer("../credentials.json")
    erowid_scraper = ErowidUrlsScraper(raise_exceptions=False, proxy_server=proxy)
    erowid_scraper.update_download_list()
    erowid_scraper.download(wait=False)


if __name__ == '__main__':
    main()
