import json
import os
import random
from time import sleep
from typing import Dict
from urllib.parse import urlparse
import logging

import requests
import requests_cache
from bs4 import BeautifulSoup, Tag, Comment, NavigableString
from newspaper import Article

requests_cache.install_cache('erowid_cache')
logging.basicConfig(level=logging.DEBUG)

class MissingExperience(Exception):
    pass


class ExperienceScraper:
    url: str
    soup: BeautifulSoup
    newspaper: Article
    exp_id: str
    save_path: str = ''
    substances_details: list = []
    story: list = []
    substances_simple: list = []
    metadata: dict = {}
    tags: list = []

    def __init__(self, url: str):
        self.url = url
        self.exp_id = urlparse(url).query.split('=')[1]

    def get_experience(self):
        """
        Retrieve the experience HTML code and input it
        for further processing
        """
        res = requests.get(self.url)

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
            if isinstance(row,Comment):
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

        drugs_chart = self.soup.find_all(class_="dosechart")[0].find_all('tr')
        for row in drugs_chart:
            amount = row.find_all(class_='dosechart-amount')[0].text.strip()
            method = row.find_all(class_='dosechart-method')[0].text.strip()
            substance_tag = row.find_all(class_='dosechart-substance')[0]
            substance_ids = substance_tag.find_all('a')
            substance_id = substance_ids[0].attrs['href'].strip() if substance_ids else ''
            substance_name = substance_tag.text.strip()
            form = row.find_all(class_='dosechart-form')[0].text.strip()
            use_time = list(row.children)[1].text.replace("DOSE:","").strip()  # time to be extracted from text
            self.substances_details.append({'use_time': use_time,
                                            'amount': amount,
                                            'method': method,
                                            'substance_id': substance_id,
                                            'substance_name': substance_name,
                                            'form': form})

    @staticmethod
    def _dict_from_str(text_str: str):
        parts = text_str.split('(')
        s = parts[0].strip()
        identifier = parts[1].strip().strip(')')
        return {'name': s, 'id': identifier}

    def extract_experience_metadata(self):
        """
        Extract other metadata, tags, and substances one-hot
        """

        footdata_tag = self.soup.find(class_='footdata')
        self.metadata = {'body_weight': self.soup.find(class_='bodyweight-amount').text.strip()}

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
                'title': self.newspaper.title}


class ErowidScraper:
    seed: int = 666
    save_folder: str = "experiences_db"
    experiences_to_download: Dict[str, ExperienceScraper] = {}
    base_url: str = "https://www.erowid.org/experiences/exp.php?ID="

    def download(self, wait: bool = False):
        """
        Download all the urls contained in urls_to_be_downloaded
        :param wait: Whether it should wait a random number of seconds (in a range) between downloads
        """
        urls_downloaded = 0
        urls_failed = 0

        for i, exp_scraper in enumerate(self.experiences_to_download.values()):
            if wait:
                sleep(random.randint(3, 20))
            try:
                logging.info(f"Downloading {exp_scraper.url}...")
                exp_scraper.get_experience()
                exp_scraper.extract_data()

                urls_downloaded += 1
                logging.info(f"success. So far {urls_downloaded} pages downloaded correctly.")
            except Exception as e:
                logging.exception('failed:')
                with open(f'exp_links/failed_urls_{type(e).__name__}.txt', 'a') as open_txt:
                    open_txt.write(exp_scraper.url)
                    open_txt.write('\n')
                urls_failed += 1
                logging.error(f"So far {urls_failed} errors.")


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
                print(f"Experience {exp_scraper.exp_id} already downloaded")
            else:
                exp_scraper.save_path = candidate_path
                self.experiences_to_download[exp_scraper.exp_id] = exp_scraper


def main():
    erowid_scraper = ErowidScraper()
    erowid_scraper.update_download_list('exp_links/mystical_experiences.txt')
    erowid_scraper.update_download_list('exp_links/bad_trips.txt')
    erowid_scraper.download()


if __name__ == '__main__':
    main()
