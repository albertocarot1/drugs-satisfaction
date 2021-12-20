"""
In this file there will be code to process the Erowid data

We want to find out whether the classification problem is approachable, and so we want to investigate on the y variable
of the problem, namely the tags.

Some of them can be actually turn into x variables (e.g. Small Groups), after analysing the data we will know how many
classes we will have, and how many data points for each class.

Some of the functions:
- return, for each tag:
  - in how many experiences it is cited
  - average of impact over experience (e.g. Bad Trip is one among three tags, the impact is 0.333)
- for each substance:
  - in how many experiences it is used
  - average of impact over experience (e.g. Marijuana is one among three substances, the impact is 0.333)
"""
import json
import logging
import re
import sys
from dataclasses import dataclass
from glob import glob
from statistics import mean
from typing import List, Dict, Union

from tqdm import tqdm
import pandas as pd

from utils import Experience

# Create logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Create STDERR handler
handler = logging.StreamHandler(sys.stderr)

# Create formatter and add it to the handler
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s', "%Y-%m-%d %H:%M:%S")
handler.setFormatter(formatter)

# Set STDERR handler as the only handler
logger.handlers = [handler]


@dataclass
class Tag:

    def __init__(self, name: str, tag_id: str, perc_usage: float):
        self.name: str = name
        self.tag_id: str = tag_id
        self.exp_appearances: int = 1

        # Percentage of experiences where the tag appears (e.g. alcohol is very common, this number will be high)
        # Basically exp_apparenaces / total_exp . Can only be calculated when total number of experiences is known.
        self.perc_exp_appearances: Union[float, None] = None

        # Percent of usage of the tag among other tags (e.g. Bad Trip is one among three tags, the usage is 0.333)
        # Average is calculated among all appearances. Can only be calculated when total number of experiences is known.
        self.perc_usages: List[float] = [perc_usage]

        self.average_impact: Union[float, None] = None

        self.co_appearances: Dict[str, int] = {}

    def calculate_stats(self, total_experiences: int):
        """
        Calculate the percentage of tag appearance in all experiences, and average impact of the tag, considering all
        the times the tag has been used.

        :param total_experiences: Total number of experiences from which tags are extracted
        """
        self.perc_exp_appearances = self.exp_appearances / total_experiences
        self.average_impact = mean(self.perc_usages)

    def to_dict(self):
        return {'name': self.name,
                'tag_id': self.tag_id,
                'exp_appearances': self.exp_appearances,
                'perc_exp_appearances': self.perc_exp_appearances,
                'perc_usages': self.perc_usages,
                'average_impact': self.average_impact}


class ErowidJSONProcessor:

    def __init__(self, json_folder: str):

        # Folder containing the JSON erowid data, one file per experience.
        self.json_folder = json_folder.rstrip('/')

        self.tags: Dict[str, Tag] = dict()

    @staticmethod
    def get_exp(exp_json_path: str) -> Experience:
        """
        Given the path to a JSON file, return an Experience object
        :param exp_json_path: path where to find the correctly formatted experience
        :return: Instantiated Experience object
        """
        if exp_json_path.find('(1)') != -1:
            logger.warning(f"Duplicate file: {exp_json_path} ")
            raise Exception
        with open(exp_json_path) as open_json:
            exp_dict = json.load(open_json)
            try:
                exp_id = re.findall(r'/(\d+)\.json', exp_json_path)[0]
            except Exception:
                logging.exception(f"Error when extracting id from json file name {exp_json_path}")
                raise
            return Experience(exp_id=exp_id,
                              title=exp_dict['title'],
                              substances_details=exp_dict['substances_details'],
                              story=exp_dict['story_paragraphs'],
                              substances_simple=exp_dict['substances_main'],
                              metadata=exp_dict['metadata'],
                              tags=exp_dict['tags'])

    def get_tags(self):
        """
        Create the stats for each Tag found in all the experiences json files.

        """
        total_experiences = 0
        for exp_json in tqdm(glob(f'{self.json_folder}/*.json')):

            total_experiences += 1
            try:
                exp = self.get_exp(exp_json)
            except:
                # Skip experience if the json cannot be parsed for any reason
                continue
            found_tags_ids = []
            for tag in exp.tags:
                if tag['id'] in ['17', '2-9']:
                    tag['id'] = '17'
                existing_tag = self.tags.get(tag['id'])
                if existing_tag:
                    self.tags[tag['id']].exp_appearances += 1
                    self.tags[tag['id']].perc_usages.append(1 / len(exp.tags))
                else:
                    self.tags[tag['id']] = Tag(name=tag['name'],
                                               tag_id=tag['id'],
                                               perc_usage=1 / len(exp.tags)
                                               )
                found_tags_ids.append(tag['id'])

            for tag in found_tags_ids:
                for co_occurring_tag in found_tags_ids:
                    if self.tags[tag].co_appearances.get(co_occurring_tag) is None:
                        self.tags[tag].co_appearances[co_occurring_tag] = 1
                    else:
                        self.tags[tag].co_appearances[co_occurring_tag] += 1
            total_experiences += 1

        for tag in self.tags.values():
            tag.calculate_stats(total_experiences)

    def get_tags_co_appearances_matrix(self) -> pd.DataFrame:
        # Return a co-appearances matrix of all the tags found in the different experiences.

        tags_co_appearances = []
        for tag in self.tags.values():
            co_appearances_titles = {self.tags[tag_id].name: co_appearances for tag_id, co_appearances in tag.co_appearances.items()}
            tags_co_appearances.append({**co_appearances_titles, 'tag_id':tag.name})

        # Create dataframe from list of dict
        tags_co_appearances_df = pd.DataFrame(tags_co_appearances)
        tags_co_appearances_df = tags_co_appearances_df.set_index('tag_id')

        # Make dataframe symmetrical
        label_union = tags_co_appearances_df.index.union(tags_co_appearances_df.columns)
        tags_co_appearances_df = tags_co_appearances_df.reindex(index=label_union, columns=label_union)
        return tags_co_appearances_df


    @staticmethod
    def process_exp(exp_dict):
        pass


def main():
    processor = ErowidJSONProcessor('../data/experiences_db')
    processor.get_tags()
    print('completed')


if __name__ == '__main__':
    main()
