import os, re, json, time, requests
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import undetected_chromedriver as uc

class ReadPage:
    BASE_TITLE_URL = "https://mangapark.io/title/"
    SEARCH_URL = "https://mangapark.io/search"
    CACHE_DIR = os.path.join("sources", "read-page")

    def __init__(self, headless: bool = True):
        self.headless = headless
        self.driver = None
        self.wait = None
        os.makedirs(self.CACHE_DIR, exist_ok=True)

    def initialize_driver(self):
        if self.driver: return  # Already initialized
        print("[INFO] Initializing ChromeDriver...")
        chrome_options = uc.ChromeOptions()

        if self.headless:
            chrome_options.add_argument("--headless=new")

        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920x1080")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")

        self.driver = uc.Chrome(options=chrome_options)
        self.wait = WebDriverWait(self.driver, 30)

        # ⚠️ Chrome 117+ headless fix
        custom_user_agent = (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/117.0.0.0 Safari/537.36"
        )
        self.driver.execute_cdp_cmd("Network.setUserAgentOverride", {"userAgent": custom_user_agent})
        print(f"[INFO] User-Agent overridden to: {custom_user_agent}")
        print("[INFO] ChromeDriver initialized successfully!")

    def _get_cache_filename(self, key: str) -> str:
        safe_name = re.sub(r'[<>:"/\\|?*]', '_', key)
        return os.path.join(self.CACHE_DIR, f"{safe_name}.json")

    def _load_from_cache(self, filepath: str):
        if os.path.exists(filepath):
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict) and "images" in data:
                        return data
                    os.remove(filepath)
            except json.JSONDecodeError:
                os.remove(filepath)
        return None

    def _save_to_cache(self, filepath: str, data):
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            print(f"✅ Saved cache to {filepath}")
        except Exception as e:
            print(f"❌ Failed to write cache: {e}")

    def _scrape_images(self, target_url: str):
        print(f"🌐 Scraping images from: {target_url}")
        self.initialize_driver()

        try:
            self.driver.get(target_url)
            self.wait.until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'div[data-name="image-show"] img'))
            )
            time.sleep(2)
            images = self.driver.find_elements(By.CSS_SELECTOR, 'div[data-name="image-show"] img')
            image_urls = [img.get_attribute('src') for img in images if img.get_attribute('src')]
            return {"images": image_urls} if image_urls else {"images": [], "error": "No images found"}
        except Exception as e:
            error_message = f"Failed to fetch images: {str(e)}"
            print("❌ " + error_message)
            return {"images": [], "error": error_message}

    def _search_latest_chapter_url(self, title: str) -> str:
        print(f"🔍 Searching for manga: {title}")
        params = {"word": title, "page": 1}
        try:
            response = requests.get(self.SEARCH_URL, params=params, timeout=15)
            if response.status_code != 200:
                print(f"❌ Search failed: {response.status_code}")
                return ""
            soup = BeautifulSoup(response.text, "html.parser")
            card = soup.find("div", {"q:key": "q4_9"})
            if not card:
                print("❌ No manga card found.")
                return ""
            latest_div = card.find("div", {"q:key": "R7_8"})
            if latest_div:
                latest_link = latest_div.find("a")
                href = latest_link.get("href", "")
                return f"https://mangapark.io{href}" if href.startswith("/") else href
            print("❌ Latest chapter not found in result.")
            return ""
        except Exception as e:
            print(f"❌ Search error: {str(e)}")
            return ""

    def _extract_info(self, url: str) -> dict:
        prefix_url = "https://mangapark.io/title/"
        if url.startswith(prefix_url):
            remaining = url[len(prefix_url):]
            parts = remaining.split("/")
            if len(parts) >= 2:
                manga_parts = parts[0].split("-")
                chapter_parts = parts[1].split("-")
                manga_title = " ".join(manga_parts[2:]) if len(manga_parts) >= 3 else parts[0].replace("-", " ")
                chapter = " ".join(chapter_parts[1:]) if len(chapter_parts) >= 2 else parts[1].replace("-", " ")
                return {"manga_title": manga_title, "chapter": chapter}
        return {"manga_title": "", "chapter": ""}

    def fetch_images(self, full_url: str):
        prefix = "http://localhost:3000/read/"
        path_part = full_url[len(prefix):] if full_url.startswith(prefix) else full_url

        if "/" in path_part:
            target_key = path_part
            target_url = self.BASE_TITLE_URL + path_part
        else:
            title = path_part.replace("%20", " ")
            latest_chapter_url = self._search_latest_chapter_url(title)
            if not latest_chapter_url:
                return {
                    "manga_title": title, "chapter": "", "images": [],
                    "resolved_path": "", "error": "No latest chapter URL found."
                }
            target_key = latest_chapter_url[len(self.BASE_TITLE_URL):]
            target_url = latest_chapter_url

        info = self._extract_info(target_url)
        cache_file = self._get_cache_filename(target_key)
        cached_data = self._load_from_cache(cache_file)

        if cached_data:
            print(f"📦 Loaded data from cache: {cache_file}")
            return cached_data

        result = self._scrape_images(target_url)
        data_to_return = {
            "manga_title": info.get("manga_title", ""),
            "chapter": info.get("chapter", ""),
            "images": result.get("images", []),
            "resolved_path": target_key
        }
        if "error" in result:
            data_to_return["error"] = result["error"]

        if data_to_return["images"]:
            self._save_to_cache(cache_file, data_to_return)

        return data_to_return

    def __del__(self):
        if self.driver:
            try:
                self.driver.quit()
                print("[INFO] ChromeDriver closed.")
            except Exception:
                pass


# Example usage
if __name__ == "__main__":
    rp = ReadPage(headless=True)
    url1 = "http://localhost:3000/read/10953-en-one-piece/8404558-chapter-1105-the-height-of-folly"
    print("Scenario 1 result:", rp.fetch_images(url1))
    url2 = "http://localhost:3000/read/One%20Piece"
    print("Scenario 2 result:", rp.fetch_images(url2))
