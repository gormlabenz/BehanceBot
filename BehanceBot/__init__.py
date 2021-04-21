import logging
import random
import time
from datetime import datetime
from pathlib import Path

import yaml
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from tinydb import Query, TinyDB


class BehanceBot():
    def __init__(self):
        Path('./logs').mkdir(parents=True, exist_ok=True)
        logging.basicConfig(
            filename='./logs/BehanceBot.log', level=logging.INFO)
        logging.getLogger().addHandler(logging.StreamHandler())

        self.db_likes = TinyDB('./logs/likes.json')
        self.db_comments = TinyDB('./logs/comments.json')
        self.db_user = TinyDB('./logs/user.json')
        self.db_User = Query()

        with open('config.yaml') as f:
            data = yaml.load(f, Loader=yaml.FullLoader)

        self.comment = data['comment']
        self.like = data['like']
        self.follow = data['follow']
        self.unfollow = data['unfollow']

        self.comment_max = data['comment_max']
        self.like_max = data['like_max']
        self.follow_max = data['follow_max']
        self.unfollow_max = data['unfollow_max']

        self.unfollow_time = data['unfollow_time']

        self.driver_path = data['driver_path']
        self.debug = data['debug']
        self.headless = data['headless']
        self.user = data['user']
        self.searches = data['Searches']
        self.searches_sort_by = data['searches_sort_by']
        self.categories = data['Categories']
        self.links = self.create_links()
        self.comments = data['Comments']

        options = Options()
        options.headless = self.headless
        options.add_argument(
            "user-data-dir=/Users/gormlabenz/Library/Application Support/Google/Chrome/")
        self.browser = webdriver.Chrome(
            executable_path=self.driver_path,
            options=options
        )
        self.actions = ActionChains(self.browser)

        self.like_count = 0
        self.comment_count = 0
        self.follow_count = 0
        self.unfollow_count = 0

        self.comment_warn = False

    def create_links(self):
        links = []

        for search in self.searches:
            link = f'https://www.behance.net/search/projects?tracking_source=typeahead_search_direct&search={search}&sort={self.searches_sort_by}'
            links.append({'topic': search, 'link': link})

        for categorie in self.categories:
            link = f'https://www.behance.net/galleries/{categorie}'
            links.append({'topic': categorie, 'link': link})

        random.shuffle(links)

        return links

    def open_link(self, link):
        self.browser.get(link)
        # self.browser.maximize_window()
        wait = WebDriverWait(self.browser, 10).until(
            EC.element_to_be_clickable((By.CLASS_NAME, "PrimaryNav-logoWrap-564")))
        time.sleep(5)

    def start_session(self):
        self.open_link('https://www.behance.net/')

        if self.check_max_unfollow:
            self.process_unfollow()

        if not self.check_max_values():
            for link in self.links:
                try:
                    logging.info(
                        f"""{datetime.now().strftime("%H:%M:%S")} Topic {link['topic']}""")
                    self.open_link(link['link'])
                    self.process_project()
                except:
                    continue

        logging.info(f'Commented: {self.comment_count} projects')
        logging.info(f'Liked: {self.like_count} projects')
        logging.info(f'Followed: {self.follow_count} users')
        logging.info(f'Unfollowed: {self.unfollow_count} users')

    def close_project_detail_page(self):
        close_button = self.browser.find_element_by_class_name(
            'rf-overlay-close')
        close_button.click()

    def like_project(self):
        like_button = self.browser.find_element_by_class_name(
            'Appreciate-wrapper-9hi')
        like_button.click()
        logging.info(f'{datetime.now().strftime("%H:%M:%S")} Liked project')
        self.like_count = self.like_count + 1

    def get_textfield(self):
        textfield = None
        try:
            textfield = self.browser.find_element_by_xpath(
                '//*[@id=\"comment\"]')
            self.actions.move_to_element(textfield)
        except NoSuchElementException:
            textfield = None
        if not textfield:
            self.close_project_detail_page()
            time.sleep(3)

        return textfield

    def check_commented(self):
        try:
            return self.browser.find_element_by_link_text(
                self.user)
        except NoSuchElementException:
            return None

    def comment_project(self, text_area, comment):
        text_area.send_keys(comment)
        time.sleep(2)
        submit_button = self.browser.find_element_by_class_name(
            'js-submit')
        submit_button.click()
        warning = self.check_comment_warning()

        if warning:
            self.comment = False
            logging.warning(
                f'{datetime.now().strftime("%H:%M:%S")} You have a block on comments, deactivated commenting.')

        """ while warning:
            logging.warning(
                f'{datetime.now().strftime("%H:%M:%S")} You have a block on comments, retrying in 60 minutes.')
            time.sleep(30 * 60)
            submit_button.click() """

        logging.info(
            f'{datetime.now().strftime("%H:%M:%S")} Comment project')
        self.comment_count = self.comment_count + 1

    def follow_user(self):
        follow_button = self.browser.find_element_by_class_name(
            'js-action-follow')
        follow_button.click()
        self.follow_count = self.follow_count + 1

        logging.info(
            f'{datetime.now().strftime("%H:%M:%S")} Followed User')

    def unfollow_user(self):
        unfollow_button = self.browser.find_element_by_class_name(
            'qa-follow-button-container')
        unfollow_button.click()

        self.unfollow_count = self.unfollow_count + 1
        time.sleep(3)

    def check_max_values(self):
        follow = True
        if self.follow_max > self.follow_count and self.unfollow:
            follow = False

        like = True
        if self.like_max > self.like_count and self.like:
            like = False

        comment = True
        if self.comment_max > self.comment_count and self.comment:
            comment = False

        if follow and like and comment:
            return True

        return False

    def check_max_unfollow(self):
        unfollow = True
        if self.unfollow_max > self.unfollow_count and self.unfollow:
            unfollow = False

        return unfollow

    def get_meta_data(self):
        user = self.browser.find_element_by_class_name('js-mini-profile').text
        project = self.browser.find_element_by_class_name(
            'Project-title-18X').text

        return {'user': user, 'project': project}

    def check_comment_warning(self):
        try:
            comment_warn = self.browser.find_element_by_class_name(
                'comment-link-warning')
        except NoSuchElementException:
            comment_warn = None

        return None

    def get_projects(self):
        root_element_class = 'ContentGrid-grid-1EY'
        root_element = self.browser.find_element_by_class_name(
            root_element_class)
        if not root_element:
            return

        projects = root_element.find_elements_by_class_name(
            'ContentGrid-gridItem-2Ad')

        if not projects:
            return

        return projects

    def process_project(self):
        projects = self.get_projects()

        for project in projects:
            if self.check_max_values():
                break

            try:
                self.actions.move_to_element(project)
                time.sleep(1)
                project.click()
                time.sleep(3)
                meta_data = self.get_meta_data()
                logging.info(
                    f'{datetime.now().strftime("%H:%M:%S")} Processing project: {meta_data["project"]} - By user: {meta_data["user"]}')
                if self.debug:
                    return
                if self.like_max > self.like_count and self.like:
                    self.like_project()
                    self.db_likes.insert(
                        {'user': meta_data['user'], 'project': meta_data['project'], 'time': time.time()})
                if self.like_max < self.like_count:
                    logging.info(
                        f'{datetime.now().strftime("%H:%M:%S")} Reached like maximum')
                if self.follow_max > self.follow_count and self.follow:
                    self.follow_user()
                    self.db_user.insert(
                        {'user': meta_data['user'], 'time': time.time()})
                if self.follow_max < self.follow_count:
                    logging.info(
                        f'{datetime.now().strftime("%H:%M:%S")} Reached follow maximum')
                if self.comment_max > self.comment_count and self.comment:
                    textfield = self.get_textfield()
                    commented = self.check_commented()
                    if textfield and not commented:
                        comment = random.choice(self.comments)
                        self.comment_project(textfield, comment)
                        self.db_comments.insert(
                            {'user': meta_data['user'], 'project': meta_data['project'], 'comment': comment, 'time': time.time()})
                if self.comment_max < self.comment_count:
                    logging.info(
                        f'{datetime.now().strftime("%H:%M:%S")} Reached comment maximum')
                time.sleep(30)
                self.close_project_detail_page()
                time.sleep(3)
            except Exception as err:
                logging.warning(
                    f'{datetime.now().strftime("%H:%M:%S")} {err}')

    def get_user(self):
        root_element = self.browser.find_element_by_class_name(
            'Following-list-1Gx')
        child_elements = root_element.find_elements_by_class_name(
            'Following-profileRowItem-2Cs')
        last_element = child_elements[-1]
        self.actions.move_to_element(last_element).perform()
        time.sleep(3)
        return child_elements

    def process_unfollow(self):
        if self.check_max_unfollow():
            print('returning')
            return

        profile_element = self.browser.find_element_by_class_name(
            'e2e-PrimaryNav-link-image')
        profile_element.click()
        time.sleep(3)

        follow_count = self.browser.find_element_by_xpath(
            '//*[@id="site-content"]/div/main/div[2]/div[1]/div[2]/div[1]/div[2]/table/tbody/tr[4]/td[2]/a')
        follow_count.click()
        time.sleep(3)

        child_elements = self.get_user()
        last_child_lengths = len(child_elements)
        child_lengths = 0

        while child_lengths is not last_child_lengths:
            child_lengths = last_child_lengths
            child_elements = self.get_user()
            last_child_lengths = len(child_elements)

        for child_element in child_elements:
            if self.check_max_unfollow():
                print('returning for')
                return

            self.actions.move_to_element(child_element)
            time.sleep(1)

            user = child_element.find_element_by_class_name(
                'e2e-ProfileRow-link').text

            user_query = self.db_user.search(self.db_User.user == user)
            print('user_query', user_query)

            if user_query and time.time() - user_query[0]['time'] > self.unfollow_time:
                self.unfollow_user()
                logging.info(
                    f'{datetime.now().strftime("%H:%M:%S")} Undfollowed user - {user}')
