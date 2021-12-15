# Drugs satisfaction - know your drugs

This project goal is to create a system that, given a setup of drugs, will let you know what kind of experience you might expect.

## Installation

In order to get the project going on the local machine, poetry must be installed

With poetry installed, run:
    
    poetry install

and then startup the virtualenv through

    poetry shell


## Dataset

The data used is scraped from Erowid, which contains experiences of users under the influence of different drugs, 
and some tags (assigned by the experiences' writers) which summarize in natural language the overall experience.

### Web scraping

Before starting to scrape, if you want to use a proxy server, make sure you have a correct `credentials.json` file
at the root of the project.

In order to start or resume the scraping project, run:

    python src/experiences_scraper.py

## Data Analysis

In order to run jupyter lab, execute the following command:

     env PYTHONPATH=<path-to-your-project>/src/ jupyter lab