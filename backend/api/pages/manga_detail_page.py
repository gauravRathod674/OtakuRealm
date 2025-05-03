import os
import sys
import json
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, unquote, urlparse, unquote_plus

def clean_text(text):
    return " ".join(text.strip().split())

def extract_manga_title_from_url(url):
    """
    Extracts the manga title from a URL of the form:
    http://localhost:3000/mangadetailpage/SOLO%20LEVELING
    It takes the last path segment, decodes any URL encoding, and returns it.
    """
    parsed_url = urlparse(url)
    path_segments = parsed_url.path.rstrip("/").split("/")
    # Assume the last segment is the manga title.
    manga_title_encoded = path_segments[-1] if path_segments else ""
    manga_title = unquote_plus(manga_title_encoded)
    return manga_title

class MangaDetailPage:
    BASE_URL = "https://mangapark.io"  # Base URL used for search and detail pages.
    SEARCH_URL = f"{BASE_URL}/search"
    HEADERS = {"User-Agent": "Mozilla/5.0"}
    
    def __init__(self, manga_title):
        # Decode URL encoded title (if any) and standardize by lower-casing.
        self.manga_title = unquote(manga_title).strip()
        self.slug = self.manga_title.lower().replace(" ", "_")
        
        # Dynamic file paths based on the manga title.
        self.DETAIL_HTML_PATH = f"sources/manga-detail-page/{self.slug}_detailpage.html"
        self.CHAPTER_HTML_PATH = self.DETAIL_HTML_PATH  # Same HTML file is used to extract chapters.
        self.JSON_PATH = f"sources/manga-detail-page/{self.slug}_manga_detail.json"
        self.HOMEPAGE_JSON_PATH = "sources/manga-homepage/homepage_data.json"

    def search_manga(self):
        """
        Searches MangaPark for the given manga title and returns the first result's detail page URL.
        """
        try:
            response = requests.get(self.SEARCH_URL, params={"word": self.manga_title}, headers=self.HEADERS, timeout=10)
            response.raise_for_status()
        except Exception as e:
            print(f"❌ Search request failed: {e}")
            return None

        soup = BeautifulSoup(response.text, "lxml")
        first_card = soup.select_one("div[q\\:key='q4_9']")
        if not first_card:
            print("❌ No manga search result found.")
            return None

        link_tag = first_card.select_one("h3[q\\:key='o2_2'] a[href]")
        if not link_tag:
            print("❌ No manga link found in result card.")
            return None

        detail_url = urljoin(self.BASE_URL, link_tag["href"])
        print(f"✅ Found manga detail URL: {detail_url}")
        return detail_url

    def fetch_html(self, url, save_path):
        """
        Fetches HTML from the given URL and saves it to the specified path.
        """
        try:
            response = requests.get(url, headers=self.HEADERS)
            if response.status_code == 200:
                with open(save_path, "w", encoding="utf-8") as file:
                    file.write(response.text)
                print(f"HTML successfully saved to {save_path}")
                return True
            else:
                print(f"Failed to fetch HTML: {response.status_code}")
                return False
        except Exception as e:
            print(f"Error fetching HTML: {e}")
            return False

    def fetch_manga_detail_from_file(self, file_path):
        """
        Extracts manga details from a local MangaPark HTML detail file.
        Returns a dictionary containing various details.
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
            soup = BeautifulSoup(html_content, 'html.parser')

            container = soup.find("div", attrs={"q:key": "g0_12"})
            if not container:
                print('Main container div with q:key="g0_12" not found.')
                return {}

            # 1) Extract image information
            image_tag = container.find("img")
            image = {}
            if image_tag:
                image['src'] = clean_text(image_tag.get("src", ""))
                image['title'] = clean_text(image_tag.get("title", ""))

            # 2) Extract authors
            authors = []
            authors_div = container.find(attrs={"q:key": "tz_4"})
            if authors_div:
                for a in authors_div.find_all("a"):
                    author = clean_text(a.get_text())
                    if author:
                        authors.append(author)

            # 3) Extract genres and remove duplicates
            genres = []
            genres_div = container.find(attrs={"q:key": "30_2"})
            if genres_div:
                for span in genres_div.find_all("span"):
                    text = clean_text(span.get_text())
                    if text and text != ",":
                        if text.endswith(","):
                            text = text[:-1]
                        genres.append(text)
                genres = list(dict.fromkeys(genres))

            # 4) Extract rating
            rating_tag = container.find("span", attrs={"q:key": "lt_0"})
            rating = clean_text(rating_tag.get_text()) if rating_tag else ""

            # 5) Extract main description
            description = ""
            desc_div = container.find("div", class_="limit-html prose lg:prose-lg")
            if desc_div:
                description = clean_text(" ".join(desc_div.stripped_strings))

            # 6) Extract extra info and publishers
            extra_info_paragraphs = []
            publishers = []
            extra_info_section = container.find("div", attrs={"q:key": "24_1"})
            if extra_info_section:
                react_island = extra_info_section.find("react-island")
                if react_island:
                    inner_div = react_island.find("div", class_="limit-html prose lg:prose-lg")
                    if inner_div:
                        for child in inner_div.children:
                            if child.name == "div" and "limit-html-p" in child.get("class", []):
                                text = clean_text(" ".join(child.stripped_strings))
                                extra_info_paragraphs.append(text)
                            elif child.name == "h6" and "Publishers:" in child.get_text():
                                ul = child.find_next_sibling("ul")
                                if ul:
                                    for li in ul.find_all("li"):
                                        publisher = clean_text(li.get_text())
                                        publishers.append(publisher)
                else:
                    paragraphs = extra_info_section.find_all("div", class_="limit-html-p")
                    extra_info_paragraphs = [clean_text(" ".join(p.stripped_strings)) for p in paragraphs]

            # 7) Languages is hardcoded for now.
            languages = "English"

            # 8) Extract MangaPark upload status
            mpark_status = ""
            mp_div = container.find(attrs={"q:key": "Yn_9"})
            if mp_div:
                mpark_status = clean_text(" ".join(mp_div.stripped_strings))
                if "Status:" in mpark_status:
                    mpark_status = clean_text(mpark_status.split("Status:")[-1])

            # 9) Extract read direction
            read_direction = ""
            rd_div = container.find(attrs={"q:key": "Yn_11"})
            if rd_div:
                read_direction = clean_text(" ".join(rd_div.stripped_strings))

            return {
                "image": image,
                "authors": authors,
                "genres": genres,
                "rating": rating,
                "description": description,
                "extra_info": extra_info_paragraphs,
                "publishers": publishers,
                "languages": languages,
                "status": mpark_status,
                "read_direction": read_direction
            }
        except FileNotFoundError:
            print(f"File not found: {file_path}")
            return {}
        except Exception as e:
            print(f"An error occurred: {e}")
            return {}

    def fetch_chapter_links_and_names_from_file(self, file_path):
        """
        Fetches chapter links and names from the local HTML file.
        Only includes chapters whose URLs start with "{BASE_URL}/title/".
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                html_content = file.read()
            soup = BeautifulSoup(html_content, 'html.parser')
            chapter_list_div = soup.find('div', {'data-name': 'chapter-list'})
            if chapter_list_div:
                links = chapter_list_div.find_all('a', href=True)
                chapter_data = []
                for link in links:
                    chapter_name = clean_text(link.get_text())
                    chapter_url = urljoin(self.BASE_URL, link['href'])
                    if chapter_url.startswith(f"{self.BASE_URL}/title/"):
                        chapter_data.append({'name': chapter_name, 'url': chapter_url})
                return chapter_data
            else:
                print('No div with data-name="chapter-list" found in the HTML file.')
                return []
        except FileNotFoundError:
            print(f"File not found: {file_path}")
            return []
        except Exception as e:
            print(f"An error occurred: {e}")
            return []

    def fetch_homepage_data(self):
        """
        Loads homepage data (if available) from a common JSON file.
        """
        if os.path.exists(self.HOMEPAGE_JSON_PATH):
            try:
                with open(self.HOMEPAGE_JSON_PATH, "r", encoding="utf-8") as file:
                    homepage_data = json.load(file)
                return homepage_data
            except Exception as e:
                print(f"Error reading homepage data: {e}")
                return {}
        else:
            print(f"Homepage JSON file not found: {self.HOMEPAGE_JSON_PATH}")
            return {}

    def get_manga_data(self):
        """
        Main method to get manga data.
          - Checks if a cached JSON exists.
          - If not, it uses the HTML file (if already saved) to extract data.
          - If the HTML file does not exist, it searches MangaPark using the manga title,
            downloads the detail page, and then extracts the data.
        It also updates the JSON with homepage data (if available).
        """
        # If JSON data is already cached, load it.
        if os.path.exists(self.JSON_PATH):
            print(f"Loading manga data from {self.JSON_PATH}...")
            with open(self.JSON_PATH, "r", encoding="utf-8") as file:
                manga_detail = json.load(file)
        else:
            # If HTML file exists, extract details.
            if os.path.exists(self.DETAIL_HTML_PATH):
                print(f"Extracting manga data from {self.DETAIL_HTML_PATH}...")
                manga_detail = self.fetch_manga_detail_from_file(self.DETAIL_HTML_PATH)
                chapter_data = self.fetch_chapter_links_and_names_from_file(self.CHAPTER_HTML_PATH)
                if manga_detail:
                    manga_detail["chapters"] = chapter_data
                    with open(self.JSON_PATH, "w", encoding="utf-8") as file:
                        json.dump(manga_detail, file, ensure_ascii=False, indent=4)
                    print(f"Manga data saved to {self.JSON_PATH}.")
                else:
                    manga_detail = {}
            else:
                # HTML file doesn't exist: perform search and fetch HTML.
                detail_url = self.search_manga()
                if detail_url:
                    if self.fetch_html(detail_url, self.DETAIL_HTML_PATH):
                        # Recurse now that the HTML is saved.
                        return self.get_manga_data()
                print("Failed to retrieve HTML.")
                manga_detail = {}

        # Merge homepage data if not already present.
        if "most_viewed" not in manga_detail or "recommended" not in manga_detail:
            homepage_data = self.fetch_homepage_data()
            if homepage_data:
                manga_detail["most_viewed"] = homepage_data.get("most_viewed", [])
                manga_detail["recommended"] = homepage_data.get("recommended", [])
                with open(self.JSON_PATH, "w", encoding="utf-8") as file:
                    json.dump(manga_detail, file, ensure_ascii=False, indent=4)
                print("Updated manga detail JSON with homepage data.")
            else:
                manga_detail.setdefault("most_viewed", [])
                manga_detail.setdefault("recommended", [])
        return manga_detail

# Example usage:
if __name__ == "__main__":
    # You can pass either the manga title or the full URL containing the title.
    # For example: python manga_detail_page.py "http://localhost:3000/mangadetailpage/SOLO%20LEVELING"
    if len(sys.argv) > 1:
        input_arg = sys.argv[1]
        # Check if the input is a URL (starts with http) or just a title.
        if input_arg.lower().startswith("http"):
            manga_title_input = extract_manga_title_from_url(input_arg)
        else:
            manga_title_input = input_arg
    else:
        manga_title_input = "SOLO LEVELING"  # Default title for testing.

    print(f"Using manga title: {manga_title_input}")
    manga_page = MangaDetailPage(manga_title_input)
    data = manga_page.get_manga_data()
    print(json.dumps(data, ensure_ascii=False, indent=4))
