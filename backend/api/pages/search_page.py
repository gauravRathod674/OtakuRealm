import os
import time
import json
import urllib.parse
import requests
import undetected_chromedriver as uc
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed

class SearchPage:
    """
    Encapsulates the search page workflow:
      - Generate a dynamic search URL using the anime title and optional filters.
      - Fetch HTML content (using undetected‑chromedriver) for page‑1.
      - Parse filter data and card data from the HTML.
      - Fetch all card data concurrently from page‑1 to the last page.
      - Return combined search results (filters and cards).
    """

    def __init__(self, anime_title: str, applied_filters: dict = None, useCache: bool = False):
        self.anime_title = anime_title
        self.applied_filters = applied_filters or {}
        self.safe_name = self.get_safe_name(anime_title)
        self.filter_str = self.generate_filter_string(self.applied_filters)
        self.base_dir = os.path.join("sources", "search-page")
        os.makedirs(self.base_dir, exist_ok=True)
        self.html_filename = os.path.join(self.base_dir, f"{self.safe_name}_{self.filter_str}_page1.html")
        self.combined_json_filename = os.path.join(self.base_dir, f"{self.safe_name}_{self.filter_str}_search.json")
        # When False, bypass any cached JSON data.
        self.useCache = useCache

    @staticmethod
    def get_safe_name(name: str) -> str:
        """Convert name to lowercase and replace spaces with underscores."""
        return name.lower().replace(" ", "_")

    @staticmethod
    def generate_filter_string(applied_filters: dict) -> str:
        """
        Generate a safe string representation of the applied_filters dictionary.
        If no filters are applied, return 'nofilter'.
        """
        if not applied_filters:
            return "nofilter"
        parts = []
        for key, value in sorted(applied_filters.items()):
            if isinstance(value, list):
                val_str = "-".join(value)
            else:
                val_str = str(value)
            safe_key = key.replace("[]", "")
            parts.append(f"{safe_key}_{val_str}")
        return "_".join(parts)

    def generate_dynamic_url(self, page: int = 1) -> str:
        """
        Generate a dynamic search URL for the given anime title, page number, and applied filters.
        """
        base_url = "https://animesugetv.to/filter"
        query_params = {"keyword": self.anime_title, "page": page}
        if self.applied_filters:
            query_params.update(self.applied_filters)
        query_string = urllib.parse.urlencode(query_params, doseq=True)
        url = f"{base_url}?{query_string}"
        print(f"Generated URL for page {page}: {url}")
        return url

    def get_html_content(self, url: str) -> str:
        """
        Return HTML content by reading an existing file or by fetching it using Selenium.
        This is used to fetch page1 HTML for filters and pagination.
        """
        if os.path.exists(self.html_filename):
            print(f"Reading existing HTML file: {self.html_filename}")
            with open(self.html_filename, "r", encoding="utf-8") as f:
                return f.read()
        else:
            print(f"{self.html_filename} not found. Fetching page from URL: {url}")
            options = uc.ChromeOptions()
            # Uncomment the next line if headless is desired:
            # options.add_argument("--headless")
            driver = uc.Chrome(options=options)
            try:
                driver.get(url)
                time.sleep(1)  # Allow dynamic content to load
                html_content = driver.page_source
                with open(self.html_filename, "w", encoding="utf-8") as f:
                    f.write(html_content)
                print(f"HTML saved as {self.html_filename}")
                return html_content
            finally:
                driver.quit()
            uc.Chrome.__del__ = lambda self: None

    def get_last_page_no(self, html: str) -> int:
        """
        Parse the provided HTML to extract the last page number from the pagination.
        Returns 1 if not found.
        """
        soup = BeautifulSoup(html, 'html.parser')
        pagination_ul = soup.find("ul", class_="pagination")
        if pagination_ul:
            last_link = pagination_ul.find("a", title="Last")
            if last_link and last_link.has_attr("href"):
                parsed = urllib.parse.urlparse(last_link["href"])
                qs = urllib.parse.parse_qs(parsed.query)
                page_no = qs.get("page")
                if page_no:
                    try:
                        return int(page_no[0])
                    except ValueError:
                        pass
        page_numbers = []
        if pagination_ul:
            for li in pagination_ul.find_all("li"):
                a = li.find("a")
                if a and a.text.isdigit():
                    try:
                        page_numbers.append(int(a.text))
                    except ValueError:
                        continue
        last_page = max(page_numbers) if page_numbers else 1
        print(f"Determined last page number: {last_page}")
        return last_page

    def fetch_filters(self, html: str) -> list:
        """
        Parse and extract filter data from the provided HTML content.
        Returns a list of dictionaries with filter titles and options.
        """
        soup = BeautifulSoup(html, 'html.parser')
        form = soup.find("form", class_=lambda x: x and "sorters" in x.split())
        if not form:
            print("Filter form not found. The page structure may be different.")
            return []
        
        filters = []
        dropdowns = form.find_all("div", class_=lambda x: x and "dropdown" in x.split() and "responsive" in x.split())
        for dropdown in dropdowns:
            title_span = dropdown.find("span", class_="value")
            if not title_span:
                continue
            filter_title = title_span.get("data-placeholder") or title_span.get_text(strip=True)
            if filter_title.lower() == "default":
                filter_title = "Sort by"
            elif filter_title.lower() == "all":
                filter_title = "Country"
            
            options = []
            dropdown_menu = dropdown.find("ul", class_=lambda x: x and "noclose" in x.split() and "dropdown-menu" in x.split())
            if not dropdown_menu:
                container = dropdown.find("div", class_=lambda x: x and "noclose" in x.split() and "dropdown-menu" in x.split())
                if container:
                    dropdown_menu = container.find("ul")
            if dropdown_menu:
                for li in dropdown_menu.find_all("li"):
                    input_tag = li.find("input")
                    label_tag = li.find("label")
                    if input_tag and label_tag:
                        name = label_tag.get_text(strip=True)
                        value = input_tag.get("value", "").strip()
                        options.append({"name": name, "value": value})
            if options:
                filters.append({"filter": filter_title, "options": options})
        print(f"Fetched {len(filters)} filters from HTML.")
        return filters

    def fetch_cards_from_html(self, html: str) -> list:
        """
        Extract card details from the provided HTML content.
        Returns a list of dictionaries with details such as title, URL, poster image, etc.
        """
        soup = BeautifulSoup(html, 'html.parser')
        cards = []
        container = soup.find("div", class_=lambda x: x and "main-card" in x.split())
        if not container:
            print("No main-card container found in the HTML.")
            return cards
        items = container.find_all("div", class_="item")
        for item in items:
            card = {}
            inner = item.find("div", class_="inner")
            if not inner:
                continue
            # Top section details
            item_top = inner.find("div", class_="item-top")
            if item_top:
                a_tag = item_top.find("a", class_="poster")
                if a_tag:
                    card["url"] = a_tag.get("href")
                    card["data_tip"] = a_tag.get("data-tip")
                    img = a_tag.find("img")
                    if img:
                        card["poster_url"] = img.get("src") or img.get("data-src")
                        card["alt"] = img.get("alt")
                status_div = item_top.find("div", class_="item-status")
                if status_div:
                    type_span = status_div.find("span", class_="type")
                    if type_span:
                        card["type"] = type_span.get_text(strip=True)
            # Bottom section details
            item_bottom = inner.find("div", class_="item-bottom")
            if item_bottom:
                name_div = item_bottom.find("div", class_="name")
                if name_div:
                    a_name = name_div.find("a")
                    if a_name:
                        card["title"] = a_name.get_text(strip=True)
                        card["japanese_title"] = a_name.get("data-jp")
                dub_sub_div = item_bottom.find("div", class_="dub-sub-total")
                if dub_sub_div:
                    sub_span = dub_sub_div.find("span", class_="sub")
                    if sub_span:
                        card["sub"] = sub_span.get_text(strip=True)
                    dub_span = dub_sub_div.find("span", class_="dub")
                    if dub_span:
                        card["dub"] = dub_span.get_text(strip=True)
            cards.append(card)
        print(f"Fetched {len(cards)} cards from HTML.")
        return cards

    def fetch_cards_for_page(self, page: int, session: requests.Session) -> tuple:
        """
        Fetch the HTML for a specific search page and extract card data.
        Returns a tuple: (page number, list of card dictionaries).
        """
        url = self.generate_dynamic_url(page)
        print(f"Fetching cards from page {page}: {url}")
        try:
            response = session.get(url, timeout=10)
            if response.status_code != 200:
                print(f"Page {page} returned status code {response.status_code}.")
                return page, []
            html = response.text
            cards = self.fetch_cards_from_html(html)
            return page, cards
        except Exception as e:
            print(f"Error on page {page}: {e}")
            return page, []

    def fetch_all_cards(self, max_workers: int = 10) -> list:
        """
        Fetch card details from multiple pages concurrently.
        Uses the page‑1 HTML to determine the last page number.
        Returns a combined list of card dictionaries.
        """
        url_page1 = self.generate_dynamic_url(page=1)
        page1_html = self.get_html_content(url_page1)
        last_page = self.get_last_page_no(page1_html)
        all_cards = []
        session = requests.Session()
        futures = {}
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            for page in range(1, last_page + 1):
                future = executor.submit(self.fetch_cards_for_page, page, session)
                futures[future] = page
            pages_results = {}
            for future in as_completed(futures):
                page, cards = future.result()
                pages_results[page] = cards
        session.close()
        for page in range(1, last_page + 1):
            cards = pages_results.get(page, [])
            if not cards:
                print(f"No cards found on page {page}.")
            all_cards.extend(cards)
        print(f"Total cards fetched from all pages: {len(all_cards)}")
        return all_cards

    def get_search_results(self) -> dict:
        """
        Retrieve the complete search results, including filter data and all card data.
        Uses a combined JSON cache file if available and if useCache is True.
        """
        if self.useCache and os.path.exists(self.combined_json_filename):
            print(f"Reading search page data from existing JSON file: {self.combined_json_filename}")
            with open(self.combined_json_filename, "r", encoding="utf-8") as f:
                search_data = json.load(f)
            return search_data
        else:
            url_page1 = self.generate_dynamic_url(page=1)
            page1_html = self.get_html_content(url_page1)
            filters = self.fetch_filters(page1_html)
            last_page = self.get_last_page_no(page1_html)
            cards = self.fetch_all_cards()
            search_data = {
                "filters": filters,
                "cards": cards,
                "last_page": last_page
            }
            with open(self.combined_json_filename, "w", encoding="utf-8") as f:
                json.dump(search_data, f, indent=3)
            print(f"Search page data saved as {self.combined_json_filename}")
            return search_data

# For local testing
if __name__ == "__main__":
    sp = SearchPage("One Piece", applied_filters={"genre[]": ["180"], "sort": "score"}, useCache=False)
    results = sp.get_search_results()
    print("\nSEARCH PAGE DATA SUMMARY:")
    print(f"Total Filters: {len(results.get('filters', []))}")
    for f in results.get("filters", []):
        print(f" - {f['filter']}: {len(f.get('options', []))} options")
    print(f"Total Cards: {len(results.get('cards', []))}\n")
    print("FULL SEARCH PAGE DATA:")
    print(json.dumps(results, indent=2))
