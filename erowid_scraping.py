import json
import logging
import os
import random
from time import sleep
from typing import Dict, Optional
from urllib.parse import urlparse

import requests
import requests_cache
from bs4 import BeautifulSoup, Tag, Comment, NavigableString

requests_cache.install_cache('erowid_cache')
logging.basicConfig(level=logging.DEBUG)


class MissingExperience(Exception):
    pass


class ProxyCredentials:
    server: str
    username: str
    password: str

    def __init__(self, cred_file):
        with open(cred_file) as open_json:
            credentials = json.load(open_json)
        self.username = credentials["username"]
        self.password = credentials["password"]
        self.server = credentials["server"]

    def get_proxy(self):
        """
        Return proxy credentials to use to make socks calls though requests
        :return: dict with credenials and server for http and https
        """
        proxy_string = f"socks5://{self.username}:{self.password}@{self.server}:1080"
        return {
            'http': proxy_string,
            'https': proxy_string
        }


class ExperienceScraper:
    url: str
    soup: BeautifulSoup
    exp_id: str
    save_path: str = ''
    title: str = ''
    substances_details: list = []
    story: list = []
    substances_simple: list = []
    metadata: dict = {}
    tags: list = []
    proxy_server: dict = {}
    was_cached: bool = False

    def __init__(self, url: str, proxy_server: Optional[Dict[str, str]] = None):
        self.url = url
        self.exp_id = urlparse(url).query.split('=')[1]
        self.proxy_server = proxy_server

    def get_experience(self):
        """
        Retrieve the experience HTML code and input it
        for further processing
        """
        res = requests.get(self.url, proxies=self.proxy_server)
        self.was_cached = res.from_cache
        self.soup = BeautifulSoup(res.content, 'html.parser')

    def extract_data(self):
        """
        Extract all data from experience
        """
        self.extract_experience_story()
        self.extract_experience_substances()
        self.extract_experience_metadata()

    def extract_experience_story(self):
        """
        Extract experience story
        """
        try:
            story_tag = self.soup.find_all(class_='report-text-surround')[0]
        except Exception:
            raise MissingExperience(f"Missing Experience report for ID {self.url}")

        save_row = False
        for row in story_tag.contents:
            if isinstance(row, Comment):
                row_str = str(row).strip()
                if row_str == 'Start Body':
                    save_row = True
                    continue
                elif row_str == 'End Body':
                    break
            if save_row and isinstance(row, NavigableString):
                row_str = str(row).strip()
                if row_str:
                    self.story.append(row_str)
        if not self.story:
            logging.warning(f"Story is empty for experience with ID {self.exp_id} ")

    def extract_experience_substances(self):
        """
        Extracts substances usage table
        """
        dosechart_tag = self.soup.find_all(class_="dosechart")
        drugs_chart = dosechart_tag[0].find_all('tr') if dosechart_tag else []
        for row in drugs_chart:
            amount_tag = row.find_all(class_='dosechart-amount')
            amount = amount_tag[0].text.strip() if amount_tag else ''

            method_tag = row.find_all(class_='dosechart-method')
            method = method_tag[0].text.strip() if method_tag else ''

            substance_tag = row.find_all(class_='dosechart-substance')[0]
            substance_ids = substance_tag.find_all('a')
            substance_id = substance_ids[0].attrs['href'].strip() if substance_ids else ''
            substance_name = substance_tag.text.strip()

            form_tag = row.find_all(class_='dosechart-form')
            form = form_tag[0].text.strip() if form_tag else ''

            use_time = list(row.children)[1].text.replace("DOSE:", "").strip()  # time to be extracted from text
            self.substances_details.append({'use_time': use_time,
                                            'amount': amount,
                                            'method': method,
                                            'substance_id': substance_id,
                                            'substance_name': substance_name,
                                            'form': form})

    @staticmethod
    def _dict_from_str(text_str: str):
        # Given a string, extract text and id and return in a dict
        text_str = text_str.strip()
        parts = text_str.split('(')
        name = parts[0].strip()
        identifier = parts[1].strip().strip(')')
        return {'name': name, 'id': identifier}

    def extract_experience_metadata(self):
        """
        Extract other metadata, tags, and substances one-hot
        """
        self.title = self.soup.find(class_='title').text.strip()
        footdata_tag = self.soup.find(class_='footdata')
        bodyweight_tag = self.soup.find(class_='bodyweight-amount')
        self.metadata = {'body_weight': bodyweight_tag.text.strip() if bodyweight_tag else ''}

        for row in footdata_tag:
            if isinstance(row, Tag):
                if len(row.contents) > 1:
                    for row_contents in row.contents:
                        text_list = row_contents.text.split(':')
                        if len(text_list) == 2:
                            self.metadata[text_list[0]] = text_list[1]
                elif "View as PDF" not in row.text.strip():
                    row_elements = row.text.split(':')
                    substances = row_elements[0].split(',')
                    for sub in substances:
                        self.substances_simple.append(self._dict_from_str(sub))
                    tags_list = row_elements[1].split(',')
                    for tag in tags_list:
                        self.tags.append(self._dict_from_str(tag))

    def save_as_json(self):
        """
        Save the experience as a JSON file in the `save_path`
        """
        with open(self.save_path, 'w') as open_json:
            json.dump(self.to_dict(), open_json, indent=4)

    def to_dict(self):

        return {'story_paragraphs': self.story,
                'substances_details': self.substances_details,
                'substances_main': self.substances_simple,
                'metadata': self.metadata,
                'tags': self.tags,
                'title': self.title}


class ErowidScraper:
    raise_exceptions: bool
    seed: int = 666
    save_folder: str = "experiences_db"
    experiences_to_download: Dict[str, ExperienceScraper] = {}
    base_url: str = "https://www.erowid.org/experiences/exp.php?ID="
    min_wait: int = 10
    max_wait: int = 30
    proxy_server: Optional[Dict[str, str]]

    def __init__(self, raise_exceptions: bool = False, proxy_server: Optional[Dict[str, str]] = None):
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
        logging.info(f"A total of {len(self.experiences_to_download)} links will be attempted to download")
        for i, exp_scraper in enumerate(self.experiences_to_download.values()):
            try:
                logging.info(f"Downloading {exp_scraper.url}...")
                exp_scraper.get_experience()
                exp_scraper.extract_data()
                exp_scraper.save_as_json()
                urls_downloaded += 1
                logging.info(f"success. So far {urls_downloaded} pages downloaded correctly.")
            except Exception as e:
                if self.raise_exceptions:
                    raise
                logging.exception('failed:')
                with open(f'exp_links/failed_urls_{type(e).__name__}.txt', 'a') as open_txt:
                    open_txt.write(exp_scraper.url)
                    open_txt.write('\n')
                urls_failed += 1
                logging.error(f"So far {urls_failed} errors.")
            if wait and not exp_scraper.was_cached:
                sleep(random.randint(self.min_wait, self.max_wait))

    def update_download_list(self, file: str = ''):
        """
        Create a list of URLs to download.
        This list can come directly from a txt file, or can be created
        with ids that might be real or not (as ids are sparse in the
        selected range).

        :param file: txt file with one URL per line
        """
        if file:
            urls = []
            with open(file) as open_txt:
                for line in open_txt:
                    if line.strip():
                        urls.append(line.strip())
        else:
            random.seed(self.seed)
            experiences_possible_ids = list(range(1, 130000))
            random.shuffle(experiences_possible_ids)
            urls = []
            for exp_id in experiences_possible_ids:
                urls.append(f"{self.base_url}{exp_id}")
        for url in urls:
            exp_scraper = ExperienceScraper(url)
            candidate_path = os.path.join(self.save_folder, f"{exp_scraper.exp_id}.json")
            if os.path.isfile(candidate_path):
                logging.info(f"Experience {exp_scraper.exp_id} already downloaded")
            else:
                exp_scraper.save_path = candidate_path
                self.experiences_to_download[exp_scraper.exp_id] = exp_scraper


def main():
    proxy = ProxyCredentials("credentials.json")
    erowid_scraper = ErowidScraper(raise_exceptions=False, proxy_server=proxy.get_proxy())
    erowid_scraper.update_download_list('exp_links/mystical_experiences.txt')
    erowid_scraper.update_download_list('exp_links/bad_trips.txt')
    erowid_scraper.update_download_list()
    erowid_scraper.download(wait=True)


if __name__ == '__main__':
    main()
