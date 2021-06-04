"""
In this file there will be code to process the Erowid data
"""
import json
from glob import glob
import os

class ErowidJSONProcessor:

    def __init__(self, json_folder: str):

        # Folder containing the JSON erowid data, one file per experience.
        self.json_folder = json_folder.rstrip('/')

    def create_csv(self, csv_path: str):
        """
        Create a CSV file, which can be open as a pandas DataFrame, and contains
        all the Erowid data.

        :param csv_path: Path where the CSV file will be saved
        """
        for exp_json in glob(f'{self.json_folder}/*.json'):
            with open(exp_json) as open_json:
                exp_dict = json.load(open_json)


def main():
    processor = ErowidJSONProcessor('../data/experiences_db')
    processor.create_csv('data/erowid_experiences.csv')

if __name__ == '__main__':
    main()
