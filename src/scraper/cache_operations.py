from typing import List

import requests
import requests_cache

from utils import from_txt_to_list

requests_cache.install_cache("data/erowid_cache")


class CacheCleaner:
    urls_to_clear: List[str] = []

    def add_urls_to_clean(self, urls: List[str]):
        self.urls_to_clear.extend(urls)

    def clean_cache_from_urls(self):
        """
        Delete all urls in `urls_to_clear` from cache
        """
        for url in self.urls_to_clear:
            requests.Session().cache.delete_url(url)


def main():
    cleaner = CacheCleaner()
    cleaner.add_urls_to_clean(from_txt_to_list('../../data/exp_links/failed_urls_ConnectionError.txt'))
    cleaner.add_urls_to_clean(from_txt_to_list('data/exp_links/failed_urls_HTTPError.txt'))
    cleaner.add_urls_to_clean(from_txt_to_list('../../data/exp_links/failed_urls_IndexError.txt'))
    cleaner.add_urls_to_clean(from_txt_to_list('data/exp_links/failed_urls_MissingExperience.txt'))
    cleaner.clean_cache_from_urls()


if __name__ == '__main__':
    main()
