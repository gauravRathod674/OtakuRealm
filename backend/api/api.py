import os 
import requests
from bs4 import BeautifulSoup
from ninja import Router, NinjaAPI
import json

api = NinjaAPI()
router = Router()


@api.get("/hello")
def hello(request):
    return {"message": "Hello from ninja-backend!"}


# ------------------------------------------------------------------
# OVERALL WORKFLOW FOR DETAIL PAGE:
#
# 1. **Dynamic Filename Generation:**
#    - Extract a base filename from the provided KAIDO_URL by removing the
#      unique numeric code at the end.
#    - Use this base to build dynamic file paths for storing HTML and JSON.
#
# 2. **File Check and Fetching:**
#    - Check if the JSON file (cache) exists.
#      - If it exists, load data from the JSON file and return it.
#      - If not, check for the HTML file.
#          - If the HTML file doesn't exist, fetch it from KAIDO_URL and save it.
#
# 3. **Parsing HTML:**
#    - Read the HTML file and use BeautifulSoup to parse the anime details.
#
# 4. **Caching Data:**
#    - Save the parsed data to a JSON file (acting as a cache) for future requests.
#
# 5. **API Endpoint:**
#    - The /scrape/kaido-detail endpoint implements the above logic,
#      returning the parsed data as JSON.
# ------------------------------------------------------------------


# Define the KAIDO URL
KAIDO_URL = "https://kaido.to/the-last-naruto-the-movie-882"


def get_base_filename(url: str) -> str:
    """
    Extract the base filename from the URL.
    Example:
      Input: "https://kaido.to/the-last-naruto-the-movie-882"
      Output: "the-last-naruto-the-movie"
    """
    # Get the last segment from the URL
    last_segment = url.rstrip("/").split("/")[-1]
    tokens = last_segment.split("-")
    # If the last token is numeric, remove it
    if tokens and tokens[-1].isdigit():
        base_filename = "-".join(tokens[:-1])
    else:
        base_filename = last_segment
    return base_filename


# Generate dynamic filenames using the base name from the URL
BASE_FILENAME = get_base_filename(KAIDO_URL)
HTML_FILE_PATH = os.path.join("sources", f"kaidoto-detail-page-{BASE_FILENAME}.html")
JSON_FILE_PATH = os.path.join("sources", f"kaidoto-detail-page-{BASE_FILENAME}.json")


def fetch_html_if_not_exists(file_path: str, url: str) -> None:
    """
    Check if the HTML file exists at file_path.
    If not, fetch the content from the URL and save it.
    """
    if not os.path.exists(file_path):
        response = requests.get(url)
        response.raise_for_status()  # Raise an exception for HTTP errors
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as file:
            file.write(response.text)


# Helper: Extract film stats from a tick container (for Related and Most Popular)
def extract_film_stats(tick_div):
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
        if parts:
            stats["type"] = parts[-1]
        else:
            stats["type"] = ""
    return stats


# Helper for Recommended Anime: Use the tick container from film-poster and the info from fd-infor
def extract_recommended_stats(anime_item):
    stats = {}
    # First, check if a tick element with class "tick-rate" exists.
    tick_rate = anime_item.select_one("div.film-poster div.tick.tick-rate")
    if tick_rate:
        stats["rate"] = tick_rate.text.strip()
    else:
        stats["rate"] = ""

    # Then extract the usual tick stats from the film-poster tick container.
    # (This may be separate from the tick-rate element.)
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

    # Then extract type and runtime from the film-detail's fd-infor container.
    fd_infor = anime_item.select_one("div.film-detail div.fd-infor")
    if fd_infor:
        # Assume the first span (that does not contain duration info) is the type.
        type_span = fd_infor.find(
            "span", class_="fdi-item", string=lambda text: text and "m" not in text
        )
        duration_span = fd_infor.find("span", class_="fdi-item fdi-duration")
        stats["type"] = type_span.text.strip() if type_span else ""
        stats["runtime"] = duration_span.text.strip() if duration_span else ""
    else:
        stats["type"] = ""
        stats["runtime"] = ""

    return stats


def parse_kaidoto_detail_page(file_path: str) -> dict:
    """
    Parse the Kaidoto anime detail page HTML file and return a dictionary
    containing:
      - Core anime details (title, poster, background, description, etc.)
      - Additional info from .anisc-info (Japanese title, synonyms, aired, etc.)
      - Genres, characters, trailers, and more seasons
      - Related anime (from the first related content block)
      - Recommended anime (from the Recommended for You section)
    """
    with open(file_path, "r", encoding="utf-8") as file:
        soup = BeautifulSoup(file, "html.parser")

    anime_data = {}

    # Title
    anime_data["title"] = soup.select_one("#ani_detail .film-name").text.strip()

    # Poster Image
    anime_data["poster"] = soup.select_one("#ani_detail .film-poster img")["src"]

    # Background Image
    cover_div = soup.select_one(".anis-cover-wrap .anis-cover")
    anime_data["background"] = (
        cover_div["style"].split("url(")[-1].split(")")[0] if cover_div else None
    )

    # Description
    anime_data["description"] = (
        soup.select_one("#ani_detail .film-description .text")
        .decode_contents()
        .strip()
    )

    film_stats = {}
    stats_container = soup.select_one("#ani_detail .film-stats")
    if stats_container:
        # Extract the ticks (rating, quality, subtitles, dubbing)
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
        # Extract type and runtime from the <span class="item"> elements following the tick div.
        span_items = stats_container.select("span.item")
        if len(span_items) >= 2:
            film_stats["type"] = span_items[0].text.strip()
            film_stats["runtime"] = span_items[1].text.strip()
    anime_data["film_stats"] = film_stats

    # Additional details initialization
    anime_data["japanese_title"] = None
    anime_data["synonyms"] = []
    anime_data["aired"] = None
    anime_data["premiered"] = None
    anime_data["duration"] = None
    anime_data["status"] = None
    anime_data["score"] = None
    anime_data["studios"] = []
    anime_data["producers"] = []

    # Loop through all detail items under .anisc-info
    for item in soup.select("#ani_detail .anisc-info .item-title"):
        head = item.select_one(".item-head").text.strip().rstrip(":")
        value = (
            item.select_one(".name").text.strip() if item.select_one(".name") else ""
        )

        if head == "Japanese":
            anime_data["japanese_title"] = value
        elif head == "Synonyms":
            anime_data["synonyms"] = [
                syn.strip() for syn in value.split(",") if syn.strip()
            ]
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

    # Genres
    anime_data["genres"] = [
        genre.text.strip()
        for genre in soup.select("#ani_detail .anisc-info .item-list a")
    ]

    # Characters & Voice Actors
    characters = []
    for character in soup.select(".block_area-actors .bac-item"):
        char_info = character.select_one(".per-info.ltr")
        char_name = char_info.select_one("h4.pi-name a").text.strip()
        char_img = char_info.select_one("a.pi-avatar img")["data-src"]
        char_role = (
            char_info.select_one("span.pi-cast").text.strip()
            if char_info.select_one("span.pi-cast")
            else ""
        )
        # Extract voice actor info safely
        va_info = character.select_one(".per-info.rtl")
        if va_info:
            va_name = va_info.select_one("h4.pi-name a").text.strip() if va_info.select_one("h4.pi-name a") else "Unknown"
            va_img = va_info.select_one("a.pi-avatar img")["data-src"] if va_info.select_one("a.pi-avatar img") else ""
            va_nationality = va_info.select_one("span.pi-cast").text.strip() if va_info.select_one("span.pi-cast") else "Unknown"
        else:
            va_name = "Unknown"
            va_img = ""
            va_nationality = "Unknown"

        characters.append(
            {
                "character": char_name,
                "char_img": char_img,
                "role": char_role,
                "voice_actor": va_name,
                "va_img": va_img,
                "nationality": va_nationality,
            }
        )
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
    related_container = soup.select_one(
        "div.block_area-content > div.cbox.cbox-list.cbox-realtime.cbox-collapse"
    )
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
                stats = extract_film_stats(tick_div)
                related_anime.append(
                    {"title": title, "url": url, "poster": poster, **stats}
                )
    anime_data["related_anime"] = related_anime

    # Extract Most Popular Anime (from the sidebar "Most Popular" section)
    most_popular = []
    popular_sections = soup.select(
        "section.block_area.block_area_sidebar.block_area-realtime"
    )
    if len(popular_sections) >= 2:
        popular_section = popular_sections[1]
        ul = popular_section.select_one("div.anif-block-ul ul")
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
                stats = extract_film_stats(tick_div)
                most_popular.append(
                    {"title": title, "url": url, "poster": poster, **stats}
                )
    anime_data["most_popular_anime"] = most_popular

    # Extract Recommended Anime (from Recommended for You Section)
    recommended_anime = []
    for anime in soup.select(".block_area_category .flw-item"):
        title_tag = anime.select_one(".film-detail .film-name a")
        title = title_tag.text.strip() if title_tag else ""
        url = title_tag.get("href", "") if title_tag else ""
        poster_tag = anime.select_one(".film-poster img")
        poster = (
            poster_tag.get("data-src", poster_tag.get("src", "")) if poster_tag else ""
        )
        stats = extract_recommended_stats(anime)
        recommended_anime.append(
            {"title": title, "url": url, "poster": poster, **stats}
        )
    anime_data["recommended_anime"] = recommended_anime

    return anime_data


@router.get("/kaido-detail", response=dict)
def get_kaido_detail(request, pathname: str = None):
    """
    If a pathname is provided (e.g., "/mo-dao-zu-shi-2nd-season-144"), then:
      1. Prepend it to "https://kaido.to" to create the target URL.
      2. Generate dynamic filenames based on this target URL.
      3. Check for cached data; if not, fetch and scrape, then return the JSON data.
    """
    # Use the provided pathname if exists, otherwise fallback to the default URL.
    target_url = f"https://kaido.to{pathname}" if pathname else KAIDO_URL

    base_filename = get_base_filename(target_url)
    html_file_path = os.path.join("sources","detail-page", f"kaidoto-detail-page-{base_filename}.html")
    json_file_path = os.path.join("sources","detail-page", f"kaidoto-detail-page-{base_filename}.json")

    if os.path.exists(json_file_path):
        with open(json_file_path, "r", encoding="utf-8") as json_file:
            data = json.load(json_file)
        return data
    else:
        fetch_html_if_not_exists(html_file_path, target_url)
        data = parse_kaidoto_detail_page(html_file_path)
        os.makedirs(os.path.dirname(json_file_path), exist_ok=True)
        with open(json_file_path, "w", encoding="utf-8") as json_file:
            json.dump(data, json_file, indent=4, ensure_ascii=False)
        return data

# Add the router to the main API instance
api.add_router("/scrape", router)

if __name__ == "__main__":
    # For testing outside of the server, always fetch and update the JSON file.
    fetch_html_if_not_exists(HTML_FILE_PATH, KAIDO_URL)
    parsed_data = parse_kaidoto_detail_page(HTML_FILE_PATH)
    os.makedirs(os.path.dirname(JSON_FILE_PATH), exist_ok=True)
    with open(JSON_FILE_PATH, "w", encoding="utf-8") as f:
        json.dump(parsed_data, f, indent=4, ensure_ascii=False)
    print(f"Data successfully written to {JSON_FILE_PATH}")