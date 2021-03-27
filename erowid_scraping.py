import json
import os
import random
from time import sleep
from typing import Dict
from urllib.parse import urlparse

import requests
import requests_cache
from bs4 import BeautifulSoup, Tag, Comment, NavigableString
from newspaper import Article

requests_cache.install_cache('erowid_cache')


class MissingExperience(Exception):
    pass


class ErowidScraper:
    seed: int = 666
    save_folder: str = "experiences_db"
    urls_to_be_downloaded: Dict[str, str]
    base_url: str = "https://www.erowid.org/experiences/exp.php?ID="

    @staticmethod
    def get_experience_id(url: str) -> str:
        """
        Return the experience's ID from the erowid url
        :param url: Erowid experience url
        :return: The experience's ID
        """
        return urlparse(url).query.split('=')[1]

    def download(self, wait: bool = False):
        """
        Download all the urls contained in urls_to_be_downloaded
        :param wait: Whether it should wait a random number of seconds (in a range) between downloads
        """
        urls_downloaded = 0
        urls_failed = 0

        for i, (url, save_path) in enumerate(self.urls_to_be_downloaded.items()):
            if wait:
                sleep(random.randint(3, 20))
            try:
                print(f"Downloading {url}...")
                downloader = ExperienceScraper(url)
                downloader.get_experience()
                downloader.extract_data()
                with open(save_path, 'w') as open_json:
                    json.dump(downloader.to_dict(), open_json)
                urls_downloaded += 1
                print(f"success. So far {urls_downloaded} pages downloaded correctly.")
            except Exception as e:
                print('failed:')
                print(repr(e))
                with open(f'exp_links/failed_urls_{type(e).__name__}.txt', 'w+') as open_txt:
                    open_txt.write(url)
                    open_txt.write('\n')
                urls_failed += 1
                print(f"So far {urls_failed} errors.")
            print()

    def update_download_list(self, file: str = ''):
        """
        Create a list of URLs to download.
        This list can come directly from a txt file, or can be created
        with ids that might be real or not (as ids are sparse in the
        selected range).

        :param file:
        """
        if file:
            urls = []
            with open(file) as open_txt:
                urls.append(open_txt.readline().strip())
        else:
            random.seed(self.seed)
            experiences_possible_ids = list(range(1, 130000))
            random.shuffle(experiences_possible_ids)
            urls = []
            for exp_id in experiences_possible_ids:
                urls.append(f"{self.base_url}{exp_id}")
        for url in urls:
            exp_id = self.get_experience_id(url)
            candidate_path = os.path.join(self.save_folder, f"{exp_id}.json")
            if os.path.isfile(candidate_path):
                print("Experience already downloaded")
            else:
                self.urls_to_be_downloaded[url] = candidate_path


class ExperienceScraper:
    url: str
    soup: BeautifulSoup
    newspaper: Article
    substances_details: list = []
    story: list = []
    substances_simple: list = []
    metadata: dict = {}
    tags: list = []

    def __init__(self, url):
        self.url = url

    def get_experience(self):
        """
        Retrieve the experience HTML code and input it
        for further processing
        """
        res = requests.get(self.url)

        self.soup = BeautifulSoup(res.content, 'html.parser')
        self.newspaper = Article(self.url)
        self.newspaper.download(input_html=res.content)
        self.newspaper.parse()

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
            raise MissingExperience("Missing Experience report for this ID")

        save_row = False
        for row in story_tag.contents:
            if type(row) == Comment:
                if str(row).strip() == 'Start Body':
                    save_row = True
                elif str(row).strip() == 'End Body':
                    save_row = False
            if save_row:
                if isinstance(row, NavigableString):
                    row_str = str(row)
                    if row_str != '\n':
                        self.story.append(row_str.strip('\n'))

    def extract_experience_substances(self):
        """
        Extracts substances usage table
        """

        drugs_chart = self.soup.find_all(class_="dosechart")[0].find_all('tr')
        for row in drugs_chart:
            amount = row.find_all(class_='dosechart-amount')[0].text
            method = row.find_all(class_='dosechart-method')[0].text
            substance_tag = row.find_all(class_='dosechart-substance')[0]
            substance_id = substance_tag.find_all('a')[0].attrs['href']
            substance_name = substance_tag.text
            form = row.find_all(class_='dosechart-form')[0].text
            use_time = list(row.children)[1].text  # time to be extracted from text
            self.substances_details.append(
                {'use_time': use_time, 'amount': amount, 'method': method, 'substance_id': substance_id,
                 'substance_name': substance_name, 'form': form})

    @staticmethod
    def _dict_from_str(text_str):
        parts = text_str.split('(')
        s = parts[0].strip()
        identifier = parts[1].strip().strip(')')
        return {'name': s, 'id': identifier}

    def extract_experience_metadata(self):
        """
        Extract other metadata, tags, and substances one-hot
        """

        footdata_tag = self.soup.find(class_='footdata')
        self.metadata = {'body_weight': self.soup.find(class_='bodyweight-amount').text}

        for row in footdata_tag:
            if type(row) == Tag:
                if len(row.contents) > 1:
                    text_list = row.contents[0].text.split(':')
                    if len(text_list) == 2:
                        self.metadata[text_list[0]] = text_list[1]
                    text_list = row.contents[1].text.split(':')
                    if len(text_list) == 2:
                        self.metadata[text_list[0]] = text_list[1]
                elif "View as PDF" not in row.text:
                    row_elements = row.text.split(':')
                    substances = row_elements[0].split(',')
                    for sub in substances:
                        self.substances_simple.append(self._dict_from_str(sub))
                    tags_list = row_elements[1].split(',')
                    for t in tags_list:
                        self.tags.append(self._dict_from_str(t))

    def to_dict(self):

        return {'story_paragraphs': self.story,
                'substances_details': self.substances_details,
                'substances_main': self.substances_simple,
                'metadata': self.metadata,
                'tags': self.tags,
                'title': self.newspaper.title}


def main():
    erowid_scraper = ErowidScraper()
    erowid_scraper.update_download_list('exp_links/mystical_experiences.txt')
    erowid_scraper.update_download_list('exp_links/bad_trips.txt')


if __name__ == '__main__':
    main()
