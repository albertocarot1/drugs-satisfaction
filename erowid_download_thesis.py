import os
import random
import json
from urllib.parse import urlparse
from time import sleep

from bs4 import BeautifulSoup, Tag, Comment, NavigableString

from torrequest import TorRequest
import requests
import requests_cache
import newspaper
requests_cache.install_cache('erowid_cache')
__author__ = 'alberto'

SEED = 666
OUT_FOLDER = "experiences_db/"
TOR_PWD = "c0eff1c1ent1stech10metr1c1"
TR = TorRequest(password=TOR_PWD)


class MissingExperience(Exception):
	pass


def get_experience(url):
	res = TR.get(url)

	soup = BeautifulSoup(res.content, 'html.parser')

	# Extract experience story
	try:
		storyTag = soup.find_all(class_='report-text-surround')[0]
	except:
		raise Exception("Missing Experience report for this ID")
	story = []
	save_row = False
	for row in storyTag.contents:
		if type(row) == Comment:
			if str(row).strip() == 'Start Body':
				save_row = True
			elif str(row).strip() == 'End Body':
				save_row = False
		if save_row:
			if type(row) == NavigableString:
				row_str = str(row)
				if row_str != '\n':
					story.append(row_str.strip('\n'))

	# Extracts substances usage table
	substances_details = []
	drugs_chart = soup.find_all(class_="dosechart")[0].find_all('tr')
	for row in drugs_chart:

		amount = row.find_all(class_='dosechart-amount')[0].text
		method = row.find_all(class_='dosechart-method')[0].text
		substanceTag = row.find_all(class_='dosechart-substance')[0]
		id = substanceTag.find_all('a')[0].attrs['href']
		substance_name = substanceTag.text
		form = row.find_all(class_='dosechart-form')[0].text
		use_time = list(row.children)[1].text  # time to be extracted from text
		substances_details.append({'use_time':use_time, 'amount':amount, 'method':method, 'substance_id':id,
								   'substance_name':substance_name, 'form':form})

	# Extract other metadata, tags, and substances one-hot
	def dict_from_str(text_str):
		parts = text_str.split('(')
		s = parts[0].strip()
		id = parts[1].strip().strip(')')
		return {'name': s, 'id': id}
	footdataTag = soup.find(class_='footdata')
	metadata = {'body_weight': soup.find(class_='bodyweight-amount').text}
	substances_simple = []
	tags = []
	for row in footdataTag:
		if type(row) == Tag:
			if len(row.contents) > 1:
				text_list = row.contents[0].text.split(':')
				if len(text_list)==2:
					metadata[text_list[0]] = text_list[1]
				text_list = row.contents[1].text.split(':')
				if len(text_list) == 2:
					metadata[text_list[0]] = text_list[1]
			elif "View as PDF" not in row.text:
				row_elements = row.text.split(':')
				substances = row_elements[0].split(',')
				for sub in substances:
					substances_simple.append(dict_from_str(sub))
				tags_list =  row_elements[1].split(',')
				for t in tags_list:
					tags.append(dict_from_str(t))

	# Extract experience text
	a = newspaper.Article(url)
	a.download(input_html=res.content)
	a.parse()

	return {'story_paragraphs':story,
			'substances_details':substances_details,
			'substances_main': substances_simple,
			'metadata':metadata,
			"tags": tags,
			'title':a.title}


def return_save_path(url):
	exp_id = urlparse(url).query.split('=')[1]
	exp_loc = OUT_FOLDER + exp_id + ".json"
	if os.path.isfile(exp_loc):
		raise Exception("Experience already saved")
	return exp_loc


def download_from_list(urls, wait=False, reset_id_every=10):
	urls_downloaded = 0
	urls_failed = 0
	already_there = 0
	failed_urls = open('failed_urls.txt', 'w+')
	for i, page in enumerate(urls):
		if wait:
			sleep(random.randint(3, 20))
		if i%reset_id_every==0:
			TR.reset_identity()  # Reset Tor
		try:
			print(f"Downloading {page}...")
			exp_loc = return_save_path(page)
			exp_data = get_experience(page)
			with open(exp_loc, 'w') as fp:
				json.dump(exp_data, fp)
			urls_downloaded += 1
			print(f"success. So far {urls_downloaded} pages downloaded correctly.")
		except (KeyboardInterrupt, SystemExit):
			failed_urls.close()
			raise
		except Exception as e:
			if e.args[0] != "Experience already saved":
				print('failed:')
				print(repr(e))
				failed_urls.write(page)
				urls_failed += 1
				print(f"So far {urls_failed} errors.")
			else:
				already_there += 1
				print(f"the page has been already downloaded! So far {already_there} cases.")
		print('\n')
	failed_urls.close()


def download_tutto():
	base_url = "https://www.erowid.org/experiences/exp.php?ID="
	random.seed(SEED)
	exps_ids = list(range(1, 130000))
	random.shuffle(exps_ids)
	urls = []
	for exp_id in exps_ids:
		urls.append(base_url + str(exp_id))
	download_from_list(urls)


def download_from_file(file):
	with open(file + '.txt') as myfile:
		urls = myfile.readlines()
	download_from_list([u.strip('\n') for u in urls])


def main():
	# positive = 'exp_links/mystical_experiences'
	# negative = 'exp_links/bad_trips'
	#
	# download_from_file(negative)
	# download_from_file(positive)
	download_tutto()


if __name__ == '__main__':
	main()
