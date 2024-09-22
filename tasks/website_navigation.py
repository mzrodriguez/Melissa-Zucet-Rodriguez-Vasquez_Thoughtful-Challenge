import os
import sys
import re
import time
import requests

import pandas as pd

from typing import Match
from datetime import datetime
from RPA.Browser.Selenium import Selenium
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from get_gecko_driver import GetGeckoDriver
from selenium.common.exceptions import (ElementNotVisibleException,
                                        NoSuchElementException,
                                        StaleElementReferenceException,
                                        ElementNotInteractableException)

firefox_driver = GetGeckoDriver()
firefox_driver.install()

class NewsWebsiteAutomation:


    def __init__(self, config:dict, logger, url_path:str, search_phrase:str, new_category:str) -> None:
        self.config = config
        self.logger = logger
        self.title = ''
        self.description = ''
        self.picture_name = ''
        self.url_path = url_path
        self.search_phrase = search_phrase
        self.category = new_category.upper()
        self.driver = Selenium()
        self.news_dataframe = pd.DataFrame(columns=['Title', 'Date', 'Description','Picture Name', 'Count of search phrases', 
                                                   'Title or description contains any amount of money'])


    def open_news_website(self) -> None:
        #apnews
        try:
            self.driver.open_browser(self.url_path, browser='firefox', service_log_path=os.path.devnull)
            time.sleep(10)
            self.driver.wait_until_element_is_visible(self.config['website']['page_header_visible_element'],120)
        except ElementNotVisibleException as e:
            self.logger.warning('reloading page, it was not possible to establish a connection')
            self.driver.reload_page()
            self.driver.wait_until_element_is_visible(self.config['website']['page_header_visible_element'],120)


    def write_to_excel(self) -> None:
        self.news_dataframe.to_excel(
                f'{self.config["excel_files_path"]}{datetime.today().strftime("%m%d%Y %H%M%S")}{self.config["excel_files_extension"]}', index=False)


    def download_pictures(self, webdriver) -> None:
        #the picture are the same as the news titles
        try:
            news_image = webdriver.find_element(By.TAG_NAME, self.config['website']['image_tag_name'])
            image_url = news_image.get_attribute('src')
            image = requests.get(image_url)
            mod_title = re.sub('|'.join(map(re.escape, self.config['signs_to_replace'])), '', self.title)
            self.picture_name = f'{self.config["downloaded_pictures_path"]}{mod_title}.{self.config["pictures_extension"]}'
            with open(self.picture_name, 'wb') as file:
                file.write(image.content)
        except NoSuchElementException as ne:
            self.picture_name = 'NA'


    def title_description_verification(self, webdriver) -> None:
        #some news have not a description, this will catch any exception with the description or title.
        try:
            self.title = webdriver.find_element(By.CLASS_NAME, self.config['website']['news_title']).text
        except NoSuchElementException as e:
            self.logger.warning('it was not possible to found a news title')
            self.title = ''
        except StaleElementReferenceException as se:
            self.logger.warning('news title is a stale element, it is necessary to update the element')
            self.title = ''
        try:
            self.description = webdriver.find_element(By.CLASS_NAME, self.config['website']['news_description']).text
        except NoSuchElementException as e:
            self.logger.warning('it was not possible to found a news description')
            self.description = ''
        except StaleElementReferenceException as se:
            self.logger.warning('news description is a stale element, it is necessary to update the element')
            self.description = ''


    def close_advertisement(self) -> None:
        #sometimes an advertisement appears in all the web page
        advertisement_box = self.driver.find_element(self.config['webdriver']['main_advertisements'])
        advertisement_box.find_element(By.XPATH, self.config['webdriver']['close_button_main_advertisement']).click()

    
    def count_search_phrase(self, title:str, description:str) -> list:
        complete_text = title + ' ' + description
        return re.findall(self.search_phrase.lower(), complete_text.lower())


    def money_in_text(self, title:str, description:str) -> Match:
        #$11.1 | 11 USD | $111,111.11 | 11 dollars
        complete_text = title + ' ' + description
        return re.search('\$|USD|dollars',complete_text)


    def get_news_information(self) -> None:
        count = 0
        search_results_table = self.driver.find_element(self.config['website']['search_results_table'])
        search_results = search_results_table.find_element(By.XPATH, self.config['website']['search_results'])
        pagelist_items = search_results.find_element(By.XPATH, self.config['website']['page_list_items'])
        results_information = pagelist_items.find_elements(By.CLASS_NAME, self.config['website']['results_information'])
        self.driver.wait_until_element_is_visible(self.config['website']['total_results'],180)
        if len(results_information) == 0:
            self.logger.info(f'No news found for {self.search_phrase}')
        else:
            count_exception = 0
            time.sleep(5)
            try:
                total_pages = self.driver.find_element('//*[@class="Pagination"]').text.split(' ')
            except StaleElementReferenceException as se:
                time.sleep(3)
                total_pages = search_results_table.find_element(By.XPATH, '//*[@class="Pagination"]').text.split(' ')
            except ElementNotVisibleException as e:
                self.close_advertisement
                total_pages = search_results_table.find_element(By.CLASS_NAME, 
                                                                self.config['website']['search_result_pages_total_number']).text.split(' ')
            
            while count <= int(total_pages[2].split('\n')[0].replace(',','')): 
                try:
                    self.driver.wait_until_element_is_visible(self.config['website']['search_results_table'], 120)
                    search_results_table = self.driver.find_element(self.config['website']['search_results_table'])
                    search_results = search_results_table.find_element(By.XPATH, self.config['website']['search_results'])
                    results_information = search_results.find_elements(By.CLASS_NAME, self.config['website']['results_information'])
                    for new in results_information:
                        self.title_description_verification(new)
                        self.download_pictures(new)
                        money_in_text = self.money_in_text(self.title, self.description)
                        matches_list = self.count_search_phrase(self.title, self.description)
                        row_to_add = [self.title, new.find_element(By.XPATH, self.config['website']['news_date']).text,
                                    self.description, self.picture_name, len(matches_list),(True if not money_in_text == None else False)]
                        self.news_dataframe.loc[len(self.news_dataframe)] = row_to_add
                    search_results_table.find_element(By.XPATH, self.config['website']['next_page']).click()
                    count+=1
                except NoSuchElementException as e:
                    if count_exception < 4:
                        self.logger.warning('it was not possible to found a required element, a page reload will be executed')
                        self.driver.reload_page()
                        self.driver.wait_until_element_is_visible(self.config['website']['total_results'],90)
                    else:
                        self.write_to_excel()
                        self.driver._quit_all_drivers()
                        sys.exit()
                    count_exception+=1
                except StaleElementReferenceException as se:
                    self.logger.warning('an element is stale at get_news_information function')
                    self.write_to_excel()
                    self.driver._quit_all_drivers()
                    sys.exit()
                except AssertionError as ae:
                    self.logger.warning(str(ae))
                    self.write_to_excel()
                    self.driver._quit_all_drivers()
                    sys.exit()
                except ElementNotInteractableException as e:
                    self.close_advertisement()
                    self.driver.wait_until_element_is_visible(self.config['website']['total_results'],90)
            self.write_to_excel()             


    def search_news(self):
        try:
            self.logger.info(f'searching for {self.search_phrase}')
            self.driver.find_element(self.config['website']['search_button']).click()
            self.driver.wait_until_element_is_enabled(self.config['website']['search_field'],120)
            self.driver.find_element(self.config['website']['search_field']).click()
            self.driver.find_element(self.config['website']['search_field']).send_keys(self.search_phrase + Keys.ENTER)
        except ElementNotVisibleException as e:
            self.close_advertisement()
            try:
                self.driver.wait_until_element_is_visible(self.config['website']['total_results'],90)
                self.driver.find_element(self.config['website']['search_field']).click()
                self.driver.find_element(self.config['website']['search_field']).send_keys(self.search_phrase + Keys.ENTER)
            except NoSuchElementException as e:
                self.driver.find_element(self.config['website']['search_field']).click()
                self.driver.find_element(self.config['website']['search_field']).send_keys(self.search_phrase + Keys.ENTER)
        #category
        self.driver.wait_until_element_is_visible(self.config['website']['filter_title_visible_element'],90)
        self.driver.find_element(self.config['website']['category_title']).click()
        category_table = self.driver.find_element(self.config['website']['category_options_table'])
        category_names = category_table.find_elements(By.CLASS_NAME, self.config['website']['category_class_name'])
        category_selected = filter(lambda x: self.category in x.text, category_names)
        list(category_selected)[0].find_element(By.TAG_NAME, 'input').click()
        self.driver.wait_until_element_is_visible(self.config['website']['clear_categories_selected'],90)
        self.get_news_information()
        self.driver._quit_all_drivers()

