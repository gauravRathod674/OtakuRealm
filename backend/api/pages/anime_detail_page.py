import os
import json
import requests
from bs4 import BeautifulSoup


class AnimeDetailPage:
    """
    Encapsulates the workflow for handling the anime detail page:
      - Dynamic file path generation based on the target URL.
      - Caching and fetching HTML if needed.
      - Parsing the HTML to extract anime details.
      - Caching the parsed data in JSON format.
    """

    DEFAULT_URL = "https://kaido.to/the-last-naruto-the-movie-882"
    INVALID_PATHS = set()

    def __init__(self, base_url: str = None):
        self.base_url = base_url or self.DEFAULT_URL

    @staticmethod
    def get_base_filename(url: str) -> str:
        """
        Extract the base filename from the URL.
        Example: "https://kaido.to/attack-on-titan-112" returns "attack-on-titan"
        """
        last_segment = url.rstrip("/").split("/")[-1]
        tokens = last_segment.split("-")
        if tokens and tokens[-1].isdigit():
            base_filename = "-".join(tokens[:-1])
        else:
            base_filename = last_segment
        return base_filename

    def get_file_paths(self, url: str) -> tuple:
        """
        Returns the HTML and JSON file paths based on the URL.
        Files are stored under sources/detail-page/.
        """
        base_filename = self.get_base_filename(url)
        html_file_path = os.path.join("sources", "detail-page", f"{base_filename}.html")
        json_file_path = os.path.join("sources", "detail-page", f"{base_filename}.json")
        return html_file_path, json_file_path

    def fetch_html_if_not_exists(self, file_path: str, url: str) -> None:
        """
        Fetch the HTML content from the URL if the file does not already exist.
        """
        base_filename = self.get_base_filename(url)
        if base_filename in self.INVALID_PATHS:
            print(f"Skipping fetch for invalid path: {base_filename}")
            return

        if not os.path.exists(file_path):
            response = requests.get(url)
            response.raise_for_status()
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, "w", encoding="utf-8") as file:
                file.write(response.text)

    @staticmethod
    def extract_film_stats(tick_div) -> dict:
        """
        Extracts film stats (subtitles, dubbing, episodes, type) from a tick container.
        """
        stats = {}
        if tick_div:
            tick_sub = tick_div.select_one("div.tick-item.tick-sub")
            tick_dub = tick_div.select_one("div.tick-item.tick-dub")
            tick_eps = tick_div.select_one("div.tick-item.tick-eps")
            stats["subtitles"] = tick_sub.text.strip() if tick_sub else ""
            stats["dubbing"] = tick_dub.text.strip() if tick_dub else ""
            stats["episodes"] = tick_eps.text.strip() if tick_eps else ""
            tick_text = tick_div.get_text(separator="|")
            parts = [p.strip() for p in tick_text.split("|") if p.strip()]
            parts = [p for p in parts if not p.isdigit()]
            stats["type"] = parts[-1] if parts else ""
        return stats

    @staticmethod
    def extract_recommended_stats(anime_item) -> dict:
        """
        Extracts stats for recommended anime items.
        """
        stats = {}
        tick_rate = anime_item.select_one("div.film-poster div.tick.tick-rate")
        stats["rate"] = tick_rate.text.strip() if tick_rate else ""

        tick_div = anime_item.select_one("div.film-poster div.tick")
        if tick_div:
            tick_sub = tick_div.select_one("div.tick-item.tick-sub")
            tick_dub = tick_div.select_one("div.tick-item.tick-dub")
            tick_eps = tick_div.select_one("div.tick-item.tick-eps")
            stats["subtitles"] = tick_sub.text.strip() if tick_sub else ""
            stats["dubbing"] = tick_dub.text.strip() if tick_dub else ""
            stats["episodes"] = tick_eps.text.strip() if tick_eps else ""
        else:
            stats["subtitles"] = ""
            stats["dubbing"] = ""
            stats["episodes"] = ""

        fd_infor = anime_item.select_one("div.film-detail div.fd-infor")
        if fd_infor:
            type_span = fd_infor.find("span", class_="fdi-item", string=lambda text: text and "m" not in text)
            duration_span = fd_infor.find("span", class_="fdi-item fdi-duration")
            stats["type"] = type_span.text.strip() if type_span else ""
            stats["runtime"] = duration_span.text.strip() if duration_span else ""
        else:
            stats["type"] = ""
            stats["runtime"] = ""
        return stats

    def parse_kaidoto_detail_page(self, file_path: str) -> dict:
        """
        Parses the HTML file and returns a dictionary with anime details.
        """
        if not os.path.exists(file_path):
            print(f"File not found: {file_path}")
            return {"error": "Invalid anime page or file does not exist."}

        with open(file_path, "r", encoding="utf-8") as file:
            soup = BeautifulSoup(file, "lxml")

        anime_data = {}

        # Core details
        anime_data["title"] = soup.select_one("#ani_detail .film-name").text.strip()
        anime_data["poster"] = soup.select_one("#ani_detail .film-poster img")["src"]
        cover_div = soup.select_one(".anis-cover-wrap .anis-cover")
        anime_data["background"] = (
            cover_div["style"].split("url(")[-1].split(")")[0] if cover_div else None
        )
        anime_data["description"] = (
            soup.select_one("#ani_detail .film-description .text").decode_contents().strip()
        )

        # Film stats
        film_stats = {}
        stats_container = soup.select_one("#ani_detail .film-stats")
        if stats_container:
            for tick in stats_container.select("div.tick .tick-item"):
                classes = tick.get("class", [])
                if "tick-pg" in classes:
                    film_stats["rating"] = tick.text.strip()
                elif "tick-quality" in classes:
                    film_stats["quality"] = tick.text.strip()
                elif "tick-sub" in classes:
                    film_stats["subtitles"] = tick.text.strip()
                elif "tick-dub" in classes:
                    film_stats["dubbing"] = tick.text.strip()
            span_items = stats_container.select("span.item")
            if len(span_items) >= 2:
                film_stats["type"] = span_items[0].text.strip()
                film_stats["runtime"] = span_items[1].text.strip()
        anime_data["film_stats"] = film_stats

        # Additional details
        anime_data["japanese_title"] = None
        anime_data["synonyms"] = []
        anime_data["aired"] = None
        anime_data["premiered"] = None
        anime_data["duration"] = None
        anime_data["status"] = None
        anime_data["score"] = None
        anime_data["studios"] = []
        anime_data["producers"] = []

        for item in soup.select("#ani_detail .anisc-info .item-title"):
            head = item.select_one(".item-head").text.strip().rstrip(":")
            value = item.select_one(".name").text.strip() if item.select_one(".name") else ""
            if head == "Japanese":
                anime_data["japanese_title"] = value
            elif head == "Synonyms":
                anime_data["synonyms"] = [syn.strip() for syn in value.split(",") if syn.strip()]
            elif head == "Aired":
                anime_data["aired"] = value
            elif head == "Premiered":
                anime_data["premiered"] = value
            elif head == "Duration":
                anime_data["duration"] = value
            elif head == "Status":
                anime_data["status"] = value
            elif head == "MAL Score":
                anime_data["score"] = value
            elif head == "Studios":
                anime_data["studios"] = [a.text.strip() for a in item.select("a")]
            elif head == "Producers":
                anime_data["producers"] = [a.text.strip() for a in item.select("a")]

        anime_data["genres"] = [genre.text.strip() for genre in soup.select("#ani_detail .anisc-info .item-list a")]

        # Characters & Voice Actors
        characters = []
        for character in soup.select(".block_area-actors .bac-item"):
            char_info = character.select_one(".per-info.ltr")
            char_name = char_info.select_one("h4.pi-name a").text.strip()
            char_img = char_info.select_one("a.pi-avatar img")["data-src"]
            char_role = (char_info.select_one("span.pi-cast").text.strip()
                         if char_info.select_one("span.pi-cast") else "")
            va_info = character.select_one(".per-info.rtl")
            if va_info:
                va_name = va_info.select_one("h4.pi-name a").text.strip() if va_info.select_one("h4.pi-name a") else "Unknown"
                va_img = va_info.select_one("a.pi-avatar img")["data-src"] if va_info.select_one("a.pi-avatar img") else ""
                va_nationality = va_info.select_one("span.pi-cast").text.strip() if va_info.select_one("span.pi-cast") else "Unknown"
            else:
                va_name = "Unknown"
                va_img = ""
                va_nationality = "Unknown"

            characters.append({
                "character": char_name,
                "char_img": char_img,
                "role": char_role,
                "voice_actor": va_name,
                "va_img": va_img,
                "nationality": va_nationality,
            })
        anime_data["characters"] = characters

        # Trailers
        trailers = []
        for trailer in soup.select(".block_area-promotions .item"):
            title = trailer.get("data-title", "").strip()
            video_url = trailer.get("data-src", "").strip()
            thumb = trailer.select_one(".screen-item-thumbnail img")["src"]
            trailers.append({"title": title, "video_url": video_url, "thumbnail": thumb})
        anime_data["trailers"] = trailers

        # More Seasons
        more_seasons = []
        for anime in soup.select(".block_area-seasons .os-item"):
            title = anime.select_one(".title").text.strip()
            url = anime["href"]
            poster_style = anime.select_one(".season-poster")["style"]
            poster = poster_style.split("url(")[-1].split(")")[0]
            more_seasons.append({"title": title, "url": url, "poster": poster})
        anime_data["more_seasons"] = more_seasons

        # Related Anime
        related_anime = []
        related_container = soup.select_one("div.block_area-content > div.cbox.cbox-list.cbox-realtime.cbox-collapse")
        if related_container:
            ul = related_container.select_one("div.anif-block-ul ul")
            if ul:
                for li in ul.find_all("li"):
                    poster_div = li.select_one("div.film-poster")
                    poster = ""
                    if poster_div:
                        img_tag = poster_div.find("img")
                        if img_tag:
                            poster = img_tag.get("data-src", img_tag.get("src", ""))
                    title_tag = li.select_one("div.film-detail h3.film-name a")
                    title = title_tag.text.strip() if title_tag else ""
                    url = title_tag.get("href", "") if title_tag else ""
                    fd_infor = li.select_one("div.film-detail div.fd-infor")
                    tick_div = fd_infor.select_one("div.tick") if fd_infor else None
                    stats = self.extract_film_stats(tick_div)
                    related_anime.append({"title": title, "url": url, "poster": poster, **stats})
        anime_data["related_anime"] = related_anime

        # Most Popular Anime (from sidebar)
        # most_popular = []
        # popular_sections = soup.select("section.block_area.block_area_sidebar.block_area-realtime")
        # if len(popular_sections) >= 2:
        #     popular_section = popular_sections[1]
        #     ul = popular_section.select_one("div.anif-block-ul ul")
        #     if ul:
        #         for li in ul.find_all("li"):
        #             poster_div = li.select_one("div.film-poster")
        #             poster = ""
        #             if poster_div:
        #                 img_tag = poster_div.find("img")
        #                 if img_tag:
        #                     poster = img_tag.get("data-src", img_tag.get("src", ""))
        #             title_tag = li.select_one("div.film-detail h3.film-name a")
        #             title = title_tag.text.strip() if title_tag else ""
        #             url = title_tag.get("href", "") if title_tag else ""
        #             fd_infor = li.select_one("div.film-detail div.fd-infor")
        #             tick_div = fd_infor.select_one("div.tick") if fd_infor else None
        #             stats = self.extract_film_stats(tick_div)
        #             most_popular.append({"title": title, "url": url, "poster": poster, **stats})
        # anime_data["most_popular_anime"] = most_popular

        # Recommended Anime
        recommended_anime = []
        for anime in soup.select(".block_area_category .flw-item"):
            title_tag = anime.select_one(".film-detail .film-name a")
            title = title_tag.text.strip() if title_tag else ""
            url = title_tag.get("href", "") if title_tag else ""
            poster_tag = anime.select_one(".film-poster img")
            poster = poster_tag.get("data-src", poster_tag.get("src", "")) if poster_tag else ""
            stats = self.extract_recommended_stats(anime)
            recommended_anime.append({"title": title, "url": url, "poster": poster, **stats})
        anime_data["recommended_anime"] = recommended_anime

        return anime_data
    
    @staticmethod
    def load_most_popular_anime():
        anime_data = {}

        try:
            with open("sources/most_popular_anime.json", "r", encoding="utf-8") as file:
                data = json.load(file)
                most_popular = data.get("most_popular_anime", [])
                anime_data["most_popular_anime"] = most_popular
                return anime_data
        except FileNotFoundError:
            print("❌ File not found: sources/most_popular_anime.json")
        except json.JSONDecodeError:
            print("❌ Error decoding JSON.")
        except Exception as e:
            print(f"❌ An unexpected error occurred: {e}")

        return anime_data


    def get_detail(self, pathname: str = None) -> dict:
        """
        Returns the parsed anime detail data.
        - Constructs the target URL (using pathname if provided).
        - Checks for cached JSON; if missing, fetches and parses HTML.
        - Appends most popular anime data to the returned result.
        """
        target_url = f"https://kaido.to{pathname}" if pathname else self.base_url
        html_file_path, json_file_path = self.get_file_paths(target_url)

        if os.path.exists(json_file_path):
            with open(json_file_path, "r", encoding="utf-8") as json_file:
                data = json.load(json_file)
        else:
            self.fetch_html_if_not_exists(html_file_path, target_url)
            data = self.parse_kaidoto_detail_page(html_file_path)
            os.makedirs(os.path.dirname(json_file_path), exist_ok=True)
            with open(json_file_path, "w", encoding="utf-8") as json_file:
                json.dump(data, json_file, indent=4, ensure_ascii=False)

        # Append most popular anime data
        most_popular_data = AnimeDetailPage.load_most_popular_anime()
        data["most_popular_anime"] = most_popular_data.get("most_popular_anime", [])

        return data



# For local testing
if __name__ == "__main__":
    page = AnimeDetailPage()
    html_path, json_path = page.get_file_paths(page.base_url)
    page.fetch_html_if_not_exists(html_path, page.base_url)
    data = page.parse_kaidoto_detail_page(html_path)
    os.makedirs(os.path.dirname(json_path), exist_ok=True)
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
    print(f"Data successfully written to {json_path}")
