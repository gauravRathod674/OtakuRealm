import os
import re
import json
import time
import concurrent.futures
from urllib.parse import urlencode
import requests
from bs4 import BeautifulSoup
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from ninja import Router
from typing import Optional
import traceback
import datetime


# Import AnimeDetailPage from the local module to avoid circular imports.
from .anime_detail_page import AnimeDetailPage

router = Router()

class AnimeFetcher:
    """Handles anime URL generation and fetching first card URL."""
    BASE_URL = "https://animesugetv.to/filter?"
    VALID_TYPES = {"Movie", "Music", "ONA", "OVA", "Special", "TV"}

    @classmethod
    def generate_anime_url(cls, title, anime_type):
        """Generate a custom URL based on title and anime type."""
        title = title.lower()
        if anime_type not in cls.VALID_TYPES:
            raise ValueError(f"Invalid type. Choose from {cls.VALID_TYPES}")
        params = {
            "keyword": title,
            "term_type[]": anime_type,
            "type": "",
            "country": "",
            "sort": "score",
        }
        return cls.BASE_URL + urlencode(params)

    @classmethod
    def get_first_card_url(cls, custom_url):
        """Fetch the first card URL for the anime."""
        response = requests.get(custom_url)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")
            first_card = soup.find("div", class_="original anime main-card")
            if first_card:
                a_tag = first_card.find("a", class_="poster tooltipstered")
                if a_tag and "href" in a_tag.attrs:
                    return a_tag["href"]
                else:
                    print("Anchor tag with the required URL not found in the first card.")
            else:
                print("No card found on the page.")
        else:
            print("Error fetching the page, status code:", response.status_code)
        return None


class VideoPageScraper:
    """Scrapes and caches video page details."""
    @staticmethod
    def fetch_video_page(url, html_path):
        """Fetch the HTML page using Selenium and save it."""
        options = uc.ChromeOptions()
        options.add_argument("--disable-gpu")
        options.add_argument("--headless")
        options.add_argument("--blink-settings=imagesEnabled=false")
        options.add_argument("--window-size=1920x1080")
        driver = uc.Chrome(options=options)
        try:
            driver.get(url)
            # Wait until the server-wrapper is present
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.CLASS_NAME, "server-wrapper"))
            )
            page_html = driver.page_source
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(page_html)
            print(f"Page HTML saved to {html_path}")
        except Exception as e:
            print("Error fetching video page:", e)
        finally:
            driver.quit()
        # Prevent driver quit issues
        uc.Chrome.__del__ = lambda self: None

    @staticmethod
    def scrape_video_page(html):
        """Scrape server and episode information from HTML."""
        soup = BeautifulSoup(html, "html.parser")
        # Part 1: Server Wrapper Info
        servers_info = {}
        server_wrapper = soup.find("div", class_="server-wrapper")
        if server_wrapper:
            server_types = server_wrapper.find_all("div", class_="server-type")
            for st in server_types:
                name_div = st.find("div", class_="name")
                type_label = (
                    name_div.get_text(separator=" ", strip=True)
                    if name_div
                    else "Unknown Type"
                )
                server_list_div = st.find("div", class_="server-list")
                servers = []
                if server_list_div:
                    for server in server_list_div.find_all("div", class_="server"):
                        span = server.find("span")
                        if span:
                            servers.append(span.get_text(strip=True))
                servers_info[type_label] = servers

        # Part 2: Media Episodes Info
        episode_ranges = {}
        media_episode = soup.find("div", id="media-episode")
        if media_episode:
            range_wrap = media_episode.find("div", class_="range-wrap")
            if range_wrap:
                for rd in range_wrap.find_all("div", class_="range"):
                    data_range = rd.get("data-range", "Unknown Range")
                    episodes = []
                    for a in rd.find_all("a"):
                        ep_number = a.get_text(strip=True)
                        ep_url = a.get("href", "").strip()
                        is_filler = "filler" in a.get("class", [])
                        episodes.append({
                            "episode": ep_number,
                            "url": ep_url,
                            "is_filler": is_filler
                        })
                    episode_ranges[data_range] = episodes

        return {"servers_info": servers_info, "episode_ranges": episode_ranges}

    @classmethod
    def scrape_and_cache(cls, first_card_url, html_path, json_cache_path):
        """
        Load or scrape video details and cache the results.
        """
        if os.path.exists(json_cache_path):
            with open(json_cache_path, "r", encoding="utf-8") as f:
                cached = json.load(f)
            timestamp = cached.get("timestamp")
            if timestamp:
                cache_time = datetime.datetime.fromisoformat(timestamp)
                if (datetime.datetime.now() - cache_time).total_seconds() < 120:
                    print(f"Loaded fresh cache from: {json_cache_path}")
                    return cached["data"]
                else:
                    print("Cache expired, refreshing...")
            else:
                print("No timestamp found, refreshing cache...")

        if not os.path.exists(html_path):
            cls.fetch_video_page(first_card_url, html_path)
            print(f"Fetched HTML and saved to {html_path}")
        else:
            print(f"Using existing HTML file: {html_path}")

        with open(html_path, "r", encoding="utf-8") as f:
            html = f.read()
        data = cls.scrape_video_page(html)

        os.makedirs(os.path.dirname(json_cache_path), exist_ok=True)
        with open(json_cache_path, "w", encoding="utf-8") as f:
            json.dump({
                "timestamp": datetime.datetime.now().isoformat(),
                "data": data
            }, f, indent=4, ensure_ascii=False)
        print(f"Scraped data saved to {json_cache_path}")
        return data

class IframeExtractor:
    """Fetches iframe src URL for the specified server."""

    @staticmethod
    def extract_anime_and_episode(url):
        """Extract anime name and episode info from URL."""
        match = re.search(r"/watch/(.*?)-([a-z0-9]+)/(ep-\d+)", url)
        if not match:
            raise ValueError("Invalid URL format. Unable to parse anime details.")
        anime_slug, _, episode_slug = match.groups()
        anime_name = anime_slug.replace("-", " ").title()
        episode_name = episode_slug.replace("ep-", "Episode ")
        return anime_name, episode_name

    @staticmethod
    def load_cache(file_name="sources/video-page/videos_cache.json", cache_type="video"):
        """Load iframe cache and remove expired entries based on cache type."""
        if not os.path.exists(file_name):
            return {}

        with open(file_name, "r") as f:
            cache = json.load(f)

        # Set expiration time based on cache type
        now = time.time()
        expiration_time = 120 if cache_type == "video" else 86400  # 120 seconds (2 mins) for video cache, 86400 seconds (1 day) for others

        keys_to_delete = []
        for key, value in cache.items():
            timestamp = value.get("timestamp")
            if not timestamp or now - timestamp > expiration_time:
                keys_to_delete.append(key)

        for key in keys_to_delete:
            del cache[key]

        return cache

    @staticmethod
    def save_cache(data, file_name="sources/video-page/videos_cache.json"):
        """Save iframe cache to a file."""
        with open(file_name, "w") as f:
            json.dump(data, f, indent=4)

    @classmethod
    def fetch_iframe_src(cls, url, category, server_name, cache_file="sources/video-page/videos_cache.json"):
        """
        Open the anime episode page and extract the iframe's src for the specified server under a given category.
        """
        anime_name, episode_name = cls.extract_anime_and_episode(url)
        cache = cls.load_cache(cache_file, cache_type="video")  # Use video cache type here
        cache_key = f"{anime_name}|{episode_name}|{category}|{server_name}"

        if cache_key in cache:
            iframe_src = cache[cache_key]["src"]
            print(f"Cache hit! Found iframe src: {iframe_src}")
            return iframe_src

        print("Cache miss. Fetching iframe src...")
        chrome_options = uc.ChromeOptions()
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--blink-settings=imagesEnabled=false")
        chrome_options.add_argument("--window-size=1920x1080")
        driver = uc.Chrome(options=chrome_options)
        iframe_src = None
        try:
            driver.get(url)
            wait = WebDriverWait(driver, 20)
            # Wait for server wrappers to load
            wait.until(EC.presence_of_all_elements_located((By.CLASS_NAME, "server-wrapper")))
            server_wrappers = driver.find_elements(By.CLASS_NAME, "server-wrapper")
            print(f"Found {len(server_wrappers)} server-wrapper elements.")

            target_server = None
            # Loop through wrappers to find the target server in the desired category.
            for wrapper in server_wrappers:
                try:
                    category_elements = wrapper.find_elements(By.CSS_SELECTOR, f"div.server-type[data-type='{category}']")
                    print(f"Found {len(category_elements)} category elements matching '{category}'.")
                    for category_element in category_elements:
                        server_list = category_element.find_elements(By.CSS_SELECTOR, "div.server")
                        for server in server_list:
                            try:
                                server_name_element = server.find_element(By.TAG_NAME, "span")
                                if server_name_element.text.strip() == server_name:
                                    target_server = server
                                    print(f"Found the server: {server_name}")
                                    break
                            except Exception as e:
                                print(f"Error finding server name element: {e}")
                        if target_server:
                            break
                    if target_server:
                        break
                except Exception as e:
                    print(f"Error processing a server-wrapper: {e}")
                    continue

            if target_server is None:
                raise Exception(f"Server '{server_name}' not found in category '{category}'.")
            
            # Click the target server to load the iframe.
            driver.execute_script("arguments[0].click();", target_server)
            print(f"Clicked on server '{server_name}'. Waiting for iframe...")
            iframe = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div#player iframe")))
            iframe_src = iframe.get_attribute("src")
            print(f"Iframe src found: {iframe_src}")
            cache[cache_key] = {
                "src": iframe_src,
                "timestamp": time.time()
            }
            cls.save_cache(cache, cache_file)
            time.sleep(2)
            return iframe_src
        except Exception as e:
            print(f"Error fetching iframe: {e}")
            return None
        finally:
            driver.quit()
            uc.Chrome.__del__ = lambda self: None


class WatchPage:
    """Main class to handle the /watch endpoint."""
    @staticmethod
    def watch(request, slug, episode, title, anime_type):
        """
        Using the provided anime title, type, slug, and episode (e.g., "/dragon-ball-z-325/ep-12"):
          - Generate the custom URL and get the first card URL.
          - Run concurrently:
              (a) Fetch the iframe src.
              (b) Scrape and cache the video page details.
              (c) Fetch anime detail page data.
          - Return a combined object with iframe_src, video_details, anime_detail, and the current episode number.
        """
        try:
            custom_url = AnimeFetcher.generate_anime_url(title, anime_type)
            print("Custom URL:", custom_url)
            first_card_url = AnimeFetcher.get_first_card_url(custom_url)
            if not first_card_url:
                return {"message": "Error: No card URL found."}
            print("First card URL:", first_card_url)

            # Use the passed episode parameter (e.g., "ep-12") to set the current episode number.
            current_episode_number = episode.replace("ep-", "") if episode.startswith("ep-") else episode

            base_filename = f"animesuge-{title.lower().replace(' ', '-').replace(':', '')}"
            print("Base filename:", base_filename)
            base_dir = os.path.join("sources", "video-page")
            os.makedirs(base_dir, exist_ok=True)
            html_path = os.path.join(base_dir, f"{base_filename}.html")
            json_cache_path = os.path.join(base_dir, f"{base_filename}.json")
            print("html_path:", html_path)
            print("json_cache_path:", json_cache_path)

            pathname = "/" + slug   

            with concurrent.futures.ThreadPoolExecutor() as executor:
                future_iframe = executor.submit(
                    IframeExtractor.fetch_iframe_src, first_card_url, "sub", "Megaplay-1"
                )
                future_video_details = executor.submit(
                    VideoPageScraper.scrape_and_cache, first_card_url, html_path, json_cache_path
                )
                anime_detail_instance = AnimeDetailPage()
                future_anime_detail = executor.submit(anime_detail_instance.get_detail, pathname)

                iframe_src = future_iframe.result()
                video_details = future_video_details.result()
                anime_detail = future_anime_detail.result() or {}  # Default to {} if None

            if not iframe_src:
                return {"message": "Error: Failed to fetch iframe src."}

            return {
                "iframe_src": iframe_src,
                "video_details": video_details,
                "anime_detail": anime_detail,
                "current_episode_number": current_episode_number,
            }
        except Exception as e:
            print("Exception occurred:", traceback.format_exc())
            return {"message": f"Error: {str(e)}"}
