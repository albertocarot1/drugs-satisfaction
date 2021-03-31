from dataclasses import dataclass
from typing import List

import requests
import requests_cache

from utils import from_txt_to_list

requests_cache.install_cache("cache_name")

@dataclass
class CacheCleaner:
    urls_to_clear: List[str]

    def clean_cache_from_urls(self):
        """
        Delete all urls in `urls_to_clear` from cache
        """
        for url in self.urls_to_clear:
            requests.Session().cache.delete_url(url)


def main():
    cleaner=CacheCleaner(from_txt_to_list(""))


if __name__ == '__main__':
    main()
