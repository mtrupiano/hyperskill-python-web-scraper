import glob
import os
import random
import re
import string
import shutil

import httpx
from bs4 import BeautifulSoup
from hstest.check_result import CheckResult
from hstest.stage_test import StageTest
from hstest.test_case import TestCase
from hstest import WrongAnswer


class BooksToScrapeScraper:
    def tag_leading_to_view_book(self, tag):
        return tag.name == "a" and tag.parent.name == "h3"

    def tag_containing_book_rating(self, tag):
        return tag.name == "p" and tag.has_attr("class") and "star-rating" in tag["class"]

    def get_book_links_of_rating(self, url, rating="Five"):
        base_url = "http://books.toscrape.com/catalogue/"
        try:
            with httpx.Client() as client:
                resp = client.get(url)
        except Exception:
            raise WrongAnswer("An error occurred when tests tried to connect to the Internet page.\n"
                              "Please, try again.")

        if resp.status_code != 200:
            return []

        soup = BeautifulSoup(resp.text, "html.parser")
        articles = soup.find_all("article", class_="product_pod")

        valid_links = []
        for article in articles:
            rating_tag = article.find(self.tag_containing_book_rating)
            if rating_tag and rating in rating_tag["class"]:
                link_tag = article.find(self.tag_leading_to_view_book)
                if link_tag:
                    href = link_tag.get("href")
                    valid_links.append(base_url + href)

        return valid_links

    def get_book_title_and_content(self, url):
        try:
            with httpx.Client() as client:
                book_resp = client.get(url)
        except Exception:
            raise WrongAnswer("An error occurred when tests tried to connect to the Internet page.\n"
                              "Please, try again.")

        soup = BeautifulSoup(book_resp.text, "html.parser")

        title = soup.find("h1")

        description_header = soup.find("div", id="product_description")
        content = description_header.find_next_sibling("p") if description_header else None

        if title and content:
            return title.text.strip(), content.text.strip()
        else:
            return title, content


class WebScraperTest(StageTest):
    def cleanup_pages(self):
        """Helper to clear Page_N folders between test cases."""
        for i in range(1, 50):
            dir_name = f"Page_{i}"
            if os.path.exists(dir_name):
                shutil.rmtree(dir_name, ignore_errors=True)

    def generate(self):
        self.cleanup_pages()

        return [
            TestCase(stdin="2\nFive", attach=(2, "Five"), time_limit=0),
            TestCase(stdin="3\nFour", attach=(3, "Four"), time_limit=0),
            TestCase(stdin="1\nOne", attach=(1, "One"), time_limit=0)
        ]

    def check(self, reply, attach=None):
        if not attach:
            return CheckResult.wrong("Attach parameter is missing.")

        num_pages, rating_type = attach
        scraper = BooksToScrapeScraper()

        for i in range(1, num_pages + 1):
            page_dir = f"Page_{i}"
            if not os.path.exists(page_dir) or not os.path.isdir(page_dir):
                return CheckResult.wrong(f"The directory '{page_dir}' was not found. "
                                         "Make sure your program creates a directory for each page iterated.")

            url = f'http://books.toscrape.com/catalogue/page-{i}.html'
            book_links = scraper.get_book_links_of_rating(url, rating_type)

            txt_files = glob.glob(os.path.join(page_dir, "*.txt"))

            if len(txt_files) != len(book_links):
                return CheckResult.wrong(f"A wrong number of files with books was found in {page_dir}. \n"
                                         f"{len(txt_files)} files were found, {len(book_links)} files were expected.")

            if not book_links:
                continue

            title, content = None, None
            while not title or not content:
                book_n = random.randint(0, len(book_links) - 1)
                title, content = scraper.get_book_title_and_content(book_links[book_n])
                if not title or not content:
                    book_links.pop(book_n)
                    if not book_links:
                        break

            if not book_links:
                continue

            clean_title = f"{title.translate(str.maketrans('', '', string.punctuation)).replace(' ', '_')}.txt"
            file_path = os.path.join(page_dir, clean_title)
            print(f"Checking for expected file: {file_path}")

            if not os.path.exists(file_path):
                return CheckResult.wrong(f"A file with the name \"{clean_title}\" was not found in {page_dir}.\n"
                                         "Make sure you remove punctuation and \nreplace the whitespaces with underscores in the titles.")

            with open(file_path, "rb") as f:
                try:
                    file_content = f.read().decode('utf-8').strip()
                except UnicodeDecodeError:
                    return CheckResult.wrong(f"An error occurred when tests tried to read the file \"{file_path}\"\n"
                                             "Please, make sure you save your file in binary format \n"
                                             "and encode the saved data using utf-8 encoding.")

            file_content = re.sub('[\r\n]', '', file_content)
            content = re.sub('[\r\n]', '', content)

            if content not in file_content:
                return CheckResult.wrong(f"Some of the files do not contain the expected book description. \n"
                                         f"The tests expected the following description:\n"
                                         f"\"{content}\"\n"
                                         f"However, the following text was found in the file {file_path}:\n"
                                         f"\"{file_content}\"")
        self.cleanup_pages()
        return CheckResult.correct()
