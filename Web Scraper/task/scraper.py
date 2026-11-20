import requests
import string
import os
from bs4 import BeautifulSoup

page_count = input()
star_rating = input()

base_url = "http://books.toscrape.com/catalogue"

for n in range(1, int(page_count) + 1):
    os.mkdir(f"Page_{n}")
    r = requests.get(f"{base_url}/page-{n}.html")
    soup = BeautifulSoup(r.content, 'html.parser')
    if r.status_code != 200:
        print(f"The URL returned {r.status_code}!")
    else:

        all_books = soup.find_all("article", class_="product_pod")
        for book in all_books:
            book_stars = book.find("p", class_="star-rating")
            if star_rating in book_stars.get("class", []):
                link = book.find("h3").find("a")
                title = link.get("title")
                title = title.rstrip()
                translator = str.maketrans('', '', string.punctuation)
                title = title.translate(translator).replace(" ", "_")
                file = open(f"Page_{n}/{title}.txt", "wb")
                book_page = requests.get(f"{base_url}/{link.get("href")}")
                book_soup = BeautifulSoup(book_page.content, 'html.parser')
                description = book_soup.find("div", id="product_description").find_next_sibling("p").get_text().rstrip()
                file.write(bytes(description, "utf-8"))
                file.close()

