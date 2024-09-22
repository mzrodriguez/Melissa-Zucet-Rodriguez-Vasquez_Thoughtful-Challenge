import sys
import logging
import yaml

import pandas as pd

from yaml.loader import SafeLoader
from datetime import datetime

from website_navigation import NewsWebsiteAutomation

logging.basicConfig(filename=f'./logs/{datetime.today().strftime("%m_%d_%Y")}.log', format='%(asctime)s - %(message)s', filemode='w')

def config_file() -> dict:
    #the category and search phrase parameter can be defined in the config file
    try:
        with open('./configuration_file/.config') as yaml_config:
            return yaml.safe_load(yaml_config)
    except IOError:
        return {}
    except yaml.YAMLError as ye:
        logging.warning('error in configuration file ' + str(ye))
        sys.exit()

config = config_file()

def main():
    newswebsite = NewsWebsiteAutomation(
            config, logging, config["webpage_url"], config["search_phrase"], 
            config["category"])
    newswebsite.open_news_website()
    newswebsite.search_news()

if __name__=="__main__":
    main()