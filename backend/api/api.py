import os
import requests
from bs4 import BeautifulSoup
from ninja import Router, NinjaAPI, Schema
import json
import re
import time
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from urllib.parse import urlencode
import concurrent.futures
import jwt
from datetime import datetime, timedelta
from pydantic import EmailStr
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.hashers import make_password
from django.conf import settings
from typing import Optional


User = get_user_model()

JWT_EXP_DELTA_SECONDS = 86400  # Token valid for 1 day

INVALID_PATHS = {"hello", "login", "dashboard"}


def generate_jwt(user):
    payload = {
        'user_id': user.id,
        'username': user.username,
        'exp': datetime.utcnow() + timedelta(seconds=JWT_EXP_DELTA_SECONDS)
    }
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")
    return token

# -------------------------------
# Pydantic Schema for Authentication
# -------------------------------
class AuthSchema(Schema):
    action: str  # "login" or "register"
    username: str
    password: str
    email: Optional[str] = None
# -------------------------------
# Validation Functions
# -------------------------------
def is_valid_username(username: str) -> bool:
    # Username must be 5-20 characters, containing letters, numbers, and underscores only.
    return bool(re.fullmatch(r'^\w{5,20}$', username))

def is_valid_password(password: str) -> bool:
    # Password must be at least 8 characters, include at least one lowercase, one uppercase,
    # one digit, and one special character.
    if len(password) < 8:
        return False
    if not re.search(r'[A-Z]', password):
        return False
    if not re.search(r'[a-z]', password):
        return False
    if not re.search(r'\d', password):
        return False
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        return False
    return True

def is_valid_email(email: str) -> bool:
    # Simple regex for validating an email address.
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return re.fullmatch(pattern, email) is not None

# -------------------------------
# Router and Endpoints
# ------------------------------

api = NinjaAPI()
router = Router()

@api.get("/hello")
def hello(request):
    return {"message": "Hello from ninja-backend!"}

# -------------------------------
# Homepage Endpoint with Caching Logic
# -------------------------------
@api.get("/")
def homepage(request):
    # Define paths for homepage HTML and JSON cache
    homepage_html_path = os.path.join("sources", "home-page", "kaido_homepage.html")
    homepage_json_path = os.path.join("sources", "home-page", "kaido_homepage.json")
    homepage_url = "https://kaido.to/home"
    
    # If JSON cache exists, load from it.
    if os.path.exists(homepage_json_path):
        with open(homepage_json_path, "r", encoding="utf-8") as json_file:
            data = json.load(json_file)
        return data
    else:
        # If HTML file exists, parse it.
        if os.path.exists(homepage_html_path):
            data = parse_kaido_homepage(homepage_html_path)
        else:
            # Fetch HTML from homepage_url and save it.
            response = requests.get(homepage_url)
            response.raise_for_status()
            os.makedirs(os.path.dirname(homepage_html_path), exist_ok=True)
            with open(homepage_html_path, "w", encoding="utf-8") as file:
                file.write(response.text)
            data = parse_kaido_homepage(homepage_html_path)
        
        # Cache parsed data to JSON file.
        os.makedirs(os.path.dirname(homepage_json_path), exist_ok=True)
        with open(homepage_json_path, "w", encoding="utf-8") as json_file:
            json.dump(data, json_file, indent=4, ensure_ascii=False)
            
        return data

def parse_kaido_homepage(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        html = f.read()
    soup = BeautifulSoup(html, "html.parser")
    
    data = {
        "image_slider": parse_image_slider(soup),
        "trending_anime": parse_trending_anime(soup),
        "top_sections": parse_top_sections(soup),
        "latest_new_upcoming": parse_latest_new_upcoming(soup),
        "genres": parse_genres(soup),
        "most_viewed": parse_most_viewed(soup),
        "footer": parse_footer(soup)
    }
    return data

def parse_image_slider(soup):
    """Extracts image slider details from the slider section."""
    slider = soup.select_one("div.deslide-wrap #slider")
    slides = []
    if slider:
        for slide in slider.select(".swiper-slide"):
            # Spotlight: in deslide-item-content, element with class 'desi-sub-text'
            spotlight = slide.select_one(".deslide-item .deslide-item-content .desi-sub-text")
            spotlight_text = spotlight.get_text(strip=True) if spotlight else ""
            # Title: in element with class 'desi-head-title'
            title_elem = slide.select_one(".deslide-item .deslide-item-content .desi-head-title")
            title = title_elem.get_text(strip=True) if title_elem else ""
            # Poster: from the image in deslide-cover-img
            poster_elem = slide.select_one(".deslide-item .deslide-cover .deslide-cover-img img")
            poster = poster_elem.get("data-src", poster_elem.get("src", "")) if poster_elem else ""
            # Detail URL: from the anchor wrapping the poster (if available)
            detail_link = slide.select_one(".desi-buttons a.btn-secondary")
            detail_url = detail_link.get("href", "") if detail_link else ""
            # Description: from element with class 'desi-description'
            description_elem = slide.select_one(".deslide-item .deslide-item-content .desi-description")
            description = description_elem.get_text(strip=True) if description_elem else ""
            # Film stats: inside .sc-detail > .scd-item, sometimes within a tick container.
            stats = {}
            tick_div = slide.select_one(".deslide-item .deslide-item-content .sc-detail .tick")
            if tick_div:
                # Often contains tick-item elements for quality, subtitles, dubbing, episodes.
                tick_sub = tick_div.select_one(".tick-item.tick-sub")
                tick_dub = tick_div.select_one(".tick-item.tick-dub")
                tick_eps = tick_div.select_one(".tick-item.tick-eps")
                stats["subtitles"] = tick_sub.get_text(strip=True) if tick_sub else ""
                stats["dubbing"] = tick_dub.get_text(strip=True) if tick_dub else ""
                stats["episodes"] = tick_eps.get_text(strip=True) if tick_eps else ""
            # Also, get type and runtime if available from a sibling (scd-item elements)
            scd_items = slide.select(".deslide-item .deslide-item-content .sc-detail .scd-item")
            if scd_items and len(scd_items) >= 2:
                stats["type"] = scd_items[0].get_text(strip=True)
                stats["runtime"] = scd_items[1].get_text(strip=True)
            slides.append({
                "spotlight": spotlight_text,
                "title": title,
                "poster": poster,
                "detail_url": detail_url,
                "description": description,
                "film_stats": stats
            })
    return slides

def parse_trending_anime(soup):
    """Extracts trending anime details (number, poster, title, url) from the Trending section."""
    trending = []
    trending_section = soup.select_one("#anime-trending")
    if trending_section:
        # The trending-list is hidden until JS shows it; we assume it's in the HTML
        for item in trending_section.select(".swiper-slide.item-qtip"):
            # Number is inside element with class 'number'
            num_elem = item.select_one(".number span")
            number = num_elem.get_text(strip=True) if num_elem else ""
            # Title and detail url
            title_elem = item.select_one(".film-title.dynamic-name")
            title = title_elem.get_text(strip=True) if title_elem else ""
            detail_link = item.select_one("a.film-poster")
            url = detail_link.get("href", "") if detail_link else ""
            # Poster: from the <img> inside film-poster
            img_elem = item.select_one("a.film-poster img")
            poster = img_elem.get("data-src", img_elem.get("src", "")) if img_elem else ""
            trending.append({
                "number": number,
                "title": title,
                "poster": poster,
                "url": url
            })
    return trending

def parse_top_sections(soup):
    """Extracts anime from sections like Top Airing, Most Popular, Most Favorite, Completed.
       For each section, extract list of anime with poster, title, subtitles, dubbing, episodes, type, anime url, and view more url.
    """
    # Create a list to store data for each section
    anime_data = []

    # Find all sections (Top Airing and Most Popular) by the class name of the parent div
    sections = soup.find_all("div", class_="col-xl-3 col-lg-6 col-md-6 col-sm-12 col-xs-12")

    # Iterate over each section and extract the necessary details
    count = 0
    for section in sections:
        section_header = section.find("div", class_="anif-block-header").text.strip()  # Get the header (e.g., Top Airing or Most Popular)
        
        # Initialize a list to store individual anime details
        anime_list = []
        
        # Find all the list items (anime) within the section
        anime_items = section.find_all("li")
        
        for item in anime_items:
            # Extract the image URL
            img_tag = item.find("img", class_="film-poster-img")
            image_url = img_tag["data-src"] if img_tag else None
            
            # Extract the title and film name
            title_tag = item.find("a", class_="dynamic-name")
            title = title_tag["title"] if title_tag else None
            url = title_tag["href"] if title_tag else None
            film_name = title_tag.text.strip() if title_tag else None
            
            # Extract tick-sub and tick-dub values
            tick_sub = item.find("div", class_="tick-sub")
            tick_sub_text = tick_sub.text.strip() if tick_sub else None
            
            tick_dub = item.find("div", class_="tick-dub")
            tick_dub_text = tick_dub.text.strip() if tick_dub else None
            
            # Extract fdi-item value
            tick_eps = item.find("div", class_="tick-eps")
            episode_text = tick_eps.text.strip() if tick_eps else None

            tick_type = item.find("div", class_="tick")
            type_text = tick_type.text.strip() if tick_type else None

            if type_text:
                type_text = re.sub(r'[^a-zA-Z]', '', type_text)

            # print(type_text)
                        
            
            # Store the extracted information in a dictionary
            anime_dict = {
                "image_url": image_url,
                "anime_title": film_name,
                "url":url,
                "subtitle": tick_sub_text,
                "dubbing": tick_dub_text,
                "episode": episode_text,
                "type": type_text
            }
            
            # Add the anime dictionary to the list
            anime_list.append(anime_dict)

        view_more_elem = section.select("div.more a")[0]
        view_more_elem_text = view_more_elem["href"] if view_more_elem else None
        count += 1
        anime_list.append({"view_more":view_more_elem_text})

        
        # Add the anime list for this section to the overall anime data
        anime_data.append({
            "section": section_header,
            "anime": anime_list
        })
    return anime_data

def parse_latest_new_upcoming(soup):
    """Extracts anime for Latest Episode, New on Kaido, Top Upcoming.
       For each card, fetch poster, title, subtitles, dubbing, episodes, type, runtime, url, and view more url.
       Returns a list of objects with keys: "section" and "anime".
    """
    sections = soup.find_all('section', class_='block_area block_area_home')
    anime_data = []

    # Loop through each section
    for section in sections:
        # Find the heading for the current section
        heading_tag = section.find('h2', class_='cat-heading')
        heading = heading_tag.text.strip() if heading_tag else "Unknown Section"

        # Get the view more link from the block header
        view_more_elem = section.find('div', class_='block_area-header')
        view_more_url = ""
        if view_more_elem:
            view_more_link = view_more_elem.find('a', class_='btn')
            if view_more_link:
                view_more_url = view_more_link['href']

        # Find all anime items in the section
        anime_items = section.find_all('div', class_='flw-item')
        
        # Initialize a list for the current section
        anime_list = []
        # First item: view more link
        anime_list.append({'view_more': view_more_url})
        
        # Loop over each anime item and extract its details
        for anime in anime_items:
            image_tag = anime.find('img', class_='film-poster-img')
            image_url = (image_tag['data-src'] if image_tag and 'data-src' in image_tag.attrs 
                         else image_tag['src'] if image_tag and 'src' in image_tag.attrs 
                         else None)
            
            anime_name_tag = anime.find('h3', class_='film-name')
            anime_name = anime_name_tag.text.strip() if anime_name_tag else None
            
            href = ""
            if anime_name_tag:
                dynamic_link = anime_name_tag.find('a', class_='dynamic-name')
                if dynamic_link and dynamic_link.has_attr("href"):
                    href = dynamic_link["href"]
            
            sub_ep_tag = anime.find('div', class_='tick-item tick-sub')
            sub_ep = sub_ep_tag.text.strip() if sub_ep_tag else None
            
            dub_ep_tag = anime.find('div', class_='tick-item tick-dub')
            dub_ep = dub_ep_tag.text.strip() if dub_ep_tag else None

            ep_tag = anime.find('div', class_='tick-item tick-eps')
            episode = ep_tag.text.strip() if ep_tag else None
            
            tv_tag = anime.find('span', class_='fdi-item')
            tv = tv_tag.text.strip() if tv_tag else None
            
            duration_tag = anime.find('span', class_='fdi-item fdi-duration')
            duration = duration_tag.text.strip() if duration_tag else None
            
            anime_list.append({
                'anime_title': anime_name,
                'url': href,
                'poster': image_url,
                'subtitle': sub_ep,
                'dubbing': dub_ep,
                'episode': episode,
                'type': tv,
                'run_time': duration,
            })
        
        # Append this section as an object to the final list
        anime_data.append({
            'section': heading,
            'anime': anime_list,
        })
    return anime_data

def parse_genres(soup):
    """Extracts all genres (name and URL) from the sidebar menu."""
    genres = []
    # Assuming genres are in a sidebar block, e.g., <ul class="nav sidebar_menu-list">
    for li in soup.select("ul.sidebar_menu-list li"):
        a = li.select_one("a.nav-link")
        if a:
            name = a.get_text(strip=True)
            url = a.get("href", "")
            genres.append({"name": name, "url": url})
    return genres

def parse_most_viewed(soup):
    """
    Extracts Most Viewed anime details for Today, Week, and Month.
    Each anime item includes: rank, image (poster URL), title, subtitles, dubbing, episodes, and URL.
    
    Assumes that the HTML source has three tab panes with IDs:
      - "top-viewed-day" for Today,
      - "top-viewed-week" for Week,
      - "top-viewed-month" for Month.
      
    The top three items have the class "item-top" in their <li> element,
    while the rest have no special li class.
    
    Returns:
        most_viewed (list): List of dictionaries with keys "category" and "data".
    """
    categories = [
        ("Today", "top-viewed-day"),
        ("Week", "top-viewed-week"),
        ("Month", "top-viewed-month"),
    ]
    
    most_viewed = []  # Array to hold the result for all categories.
    
    for category, tab_id in categories:
        data = []
        tab_content = soup.find("div", id=tab_id)
        if tab_content:
            # Select all li items (top 3 have class "item-top", others don't)
            li_items = tab_content.find("ul", class_="ulclear").find_all("li")
            for li in li_items:
                # Extract rank from "div.film-number span"
                rank_elem = li.find("div", class_="film-number")
                rank = rank_elem.get_text(strip=True) if rank_elem else ""
                
                # Extract image URL from the <img> in "div.film-poster"
                poster_elem = li.find("div", class_="film-poster")
                img_tag = poster_elem.find("img") if poster_elem else None
                image_url = ""
                if img_tag:
                    image_url = img_tag.get("data-src") or img_tag.get("src") or ""
                
                # Extract title and URL from "div.film-detail h3.film-name a"
                title_elem = li.find("h3", class_="film-name")
                title = ""
                url = ""
                if title_elem:
                    a_tag = title_elem.find("a")
                    if a_tag:
                        title = a_tag.get_text(strip=True)
                        url = a_tag.get("href", "")
                
                # Extract subtitles, dubbing, and episodes from the "fd-infor" section
                subtitles = ""
                dubbing = ""
                episodes = ""
                fd_infor = li.find("div", class_="fd-infor")
                if fd_infor:
                    tick_sub = fd_infor.find("div", class_="tick-item tick-sub")
                    tick_dub = fd_infor.find("div", class_="tick-item tick-dub")
                    tick_eps = fd_infor.find("div", class_="tick-item tick-eps")
                    subtitles = tick_sub.get_text(strip=True) if tick_sub else ""
                    dubbing = tick_dub.get_text(strip=True) if tick_dub else ""
                    episodes = tick_eps.get_text(strip=True) if tick_eps else ""
                
                data.append({
                    "rank": rank,
                    "image": image_url,
                    "title": title,
                    "url": url,
                    "subtitles": subtitles,
                    "dubbing": dubbing,
                    "episodes": episodes
                })
        most_viewed.append({
            "category": category,
            "data": data
        })
    
    return most_viewed

def parse_footer(soup):
    """Extracts Footer A-Z List links (All, #, 0-9, A-Z)"""
    footer_links = []
    # Assuming the footer A-Z list is in a container with a known class/id (e.g., "footer-a-z")
    # You might need to adjust this selector based on the actual HTML structure.
    for link in soup.select('.az-list li a'):
        footer_links.append({
            'text': link.get_text(strip=True),
            'url': link['href']
        })
    return footer_links


@api.get("/login")
def login(request):
    return {"message": "Login page from backend!"}

@api.post("/login")
def auth(request, data: AuthSchema):
    action = data.action.lower().strip()
    username = data.username.strip()
    password = data.password

    if action == "register":
        if not is_valid_username(username):
            return {"success": False, "message": "Username must be 5-20 characters and contain only letters, numbers, and underscores."}
        if not data.email or not is_valid_email(data.email):
            return {"success": False, "message": "Please provide a valid email address."}
        if not is_valid_password(password):
            return {"success": False, "message": "Password must be at least 8 characters long and include uppercase, lowercase, digit, and special character."}
        if User.objects.filter(username=username).exists():
            return {"success": False, "message": "Username already exists."}
        try:
            user = User.objects.create(
                username=username,
                email=data.email,
                password=make_password(password)
            )
            return {"success": True, "message": "Registration successful! Please log in."}
        except Exception as e:
            return {"success": False, "message": f"Registration error: {str(e)}"}
    elif action == "login":
        user = authenticate(username=username, password=password)
        if user is None:
            return {"success": False, "message": "Invalid username or password."}
        try:
            token = generate_jwt(user)
            return {"success": True, "message": "Login successful!", "token": token}
        except Exception as e:
            return {"success": False, "message": f"Error generating token: {str(e)}"}
    else:
        return {"success": False, "message": "Invalid action. Use 'login' or 'register'."}


@api.get("/watch/{slug}", response=dict)
def watch(request, slug: str, title: str, anime_type: str):
    """
    Using the provided anime title, type, and slug (e.g., "/dragon-ball-z-325"):
      - Generate the custom URL and get the first card URL.
      - Run concurrently:
          (a) Fetch the iframe src using fetch_iframe_src().
          (b) Scrape and cache the video page details.
          (c) Fetch anime detail page data using get_kaido_detail() with pathname="/" + slug.
      - Return a combined object with:
          - iframe_src
          - video_details (servers and episodes)
          - anime_detail (recommendations, related, seasons, etc.)
    """
    try:
        custom_url = generate_anime_url(title, anime_type)
        print("Custom URL:", custom_url)
        first_card_url = get_first_card_url(custom_url)
        if not first_card_url:
            return {"message": "Error: No card URL found."}
        print("First card URL:", first_card_url)

        # Parse the episode number from the last segment "ep-18" => "18"
        ep_match = re.search(r"/ep-(\d+)$", first_card_url)
        if ep_match:
            current_episode_number = ep_match.group(1)
        else:
            current_episode_number = "??"  # Fallback if not found

        # Define dynamic file paths for video page caching
        base_filename = f"animesuge-{title.lower().replace(' ', '-').replace(':', '')}"
        print("Base filename:", base_filename)
        base_dir = os.path.join("sources", "video-page")
        os.makedirs(base_dir, exist_ok=True)
        html_path = os.path.join(base_dir, f"{base_filename}.html")
        print("html_path : ", html_path)
        json_cache_path = os.path.join(base_dir, f"{base_filename}.json")
        print("json_path : ", json_cache_path)

        # Use ThreadPoolExecutor to run tasks concurrently.
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future_iframe = executor.submit(
                fetch_iframe_src, first_card_url, "sub", "VidPlay"
            )
            future_video_details = executor.submit(
                scrape_and_cache, first_card_url, html_path, json_cache_path
            )
            # Use the slug from the URL to build the pathname (prepend a "/")
            pathname = "/" + slug
            future_anime_detail = executor.submit(get_kaido_detail, request, pathname)

            # Wait for tasks to complete.
            iframe_src = future_iframe.result()
            # The scrape_and_cache function now returns the data from JSON (or scraped)
            video_details = future_video_details.result()
            anime_detail = future_anime_detail.result()

        if not iframe_src:
            return {"message": "Error: Failed to fetch iframe src."}

        return {
            "iframe_src": iframe_src,
            "video_details": video_details,
            "anime_detail": anime_detail,
            "current_episode_number": current_episode_number,
        }
    except Exception as e:
        return {"message": f"Error: {str(e)}"}


# ----------------- Part 1: Generate Custom URL and Fetch First Card URL -----------------


def generate_anime_url(title: str, anime_type: str):
    title = title.lower()
    valid_types = {"Movie", "Music", "ONA", "OVA", "Special", "TV"}

    # Validate the anime type
    if anime_type not in valid_types:
        raise ValueError(f"Invalid type. Choose from {valid_types}")

    # Encode query parameters
    params = {
        "keyword": title,
        "term_type[]": anime_type,
        "type": "",
        "country": "",
        "sort": "score",
    }

    base_url = "https://animesugetv.to/filter?"
    return base_url + urlencode(params)


def get_first_card_url(custom_url):
    response = requests.get(custom_url)
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, "html.parser")

        # Find the first card/item
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


def fetch_video_page(url, html_path):
    options = uc.ChromeOptions()
    options.add_argument("--disable-gpu")
    # Uncomment if headless is desired:
    options.add_argument("--headless")
    options.add_argument("--blink-settings=imagesEnabled=false")
    options.add_argument("--window-size=1920x1080")
    driver = uc.Chrome(options=options)
    try:
        driver.get(url)
        while True:
            try:
                if driver.find_element(By.CLASS_NAME, "server-wrapper"):
                    break  # Exit loop when element is found
            except:
                pass  # Keep retrying
            time.sleep(1)  # Wait 1 second before retrying
        page_html = driver.page_source
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(page_html)
        print(f"Page HTML saved to {html_path}")
    except Exception as e:
        print("Error fetching video page:", e)
    finally:
        driver.quit()
    uc.Chrome.__del__ = lambda self: None


def scrape_video_page(html):
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
                    
                    # Check if episode is a filler or not
                    is_filler = "filler" in a.get("class", [])
                    
                    episodes.append({
                        "episode": ep_number,
                        "url": ep_url,
                        "is_filler": is_filler
                    })
                episode_ranges[data_range] = episodes

    return {"servers_info": servers_info, "episode_ranges": episode_ranges}

def scrape_and_cache(first_card_url, html_path, json_cache_path):
    """
    Workflow:
      1. If the JSON file exists, load and return its content.
      2. Otherwise, check for the HTML file.
         - If HTML exists, load it.
         - If not, fetch the HTML page.
      3. Scrape the HTML for video details.
      4. Save the scraped data to the JSON file.
      5. Return the scraped data.
    """
    # 1. Check if JSON file exists
    if os.path.exists(json_cache_path):
        with open(json_cache_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        print(f"Loaded video details from existing JSON cache: {json_cache_path}")
        return data

    # 2. Check if HTML file exists; if not, fetch it.
    if not os.path.exists(html_path):
        fetch_video_page(first_card_url, html_path)
        print(f"Fetched HTML and saved to {html_path}")
    else:
        print(f"Using existing HTML file: {html_path}")

    # 3. Load HTML and scrape
    with open(html_path, "r", encoding="utf-8") as f:
        html = f.read()
    data = scrape_video_page(html)

    # 4. Save scraped data to JSON cache
    os.makedirs(os.path.dirname(json_cache_path), exist_ok=True)
    with open(json_cache_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
    print(f"Scraped data saved to {json_cache_path}")
    
    # 5. Return the scraped data
    return data

# ----------------- Part 2: Extract Iframe Src using Selenium & undetected_chromedriver -----------------


def extract_anime_and_episode(url):
    """
    Extract anime name and episode information from the given URL.
    """
    # Regex to parse anime name and episode number
    match = re.search(r"/watch/(.*?)-([a-z0-9]+)/(ep-\d+)", url)
    if not match:
        raise ValueError(
            "URL format is invalid. Unable to extract anime and episode information."
        )

    anime_slug, _, episode_slug = match.groups()
    # Replace hyphens with spaces and title-case for better readability
    anime_name = anime_slug.replace("-", " ").title()
    episode_name = episode_slug.replace("ep-", "Episode ")
    return anime_name, episode_name


def load_cache(file_name="sources/video-page/videos_cache.json"):
    """Load the cache from the file."""
    if os.path.exists(file_name):
        with open(file_name, "r") as f:
            return json.load(f)
    return {}


def save_cache(data, file_name="sources/video-page/videos_cache.json"):
    """Save the cache to the file."""
    with open(file_name, "w") as f:
        json.dump(data, f, indent=4)


def fetch_iframe_src(
    url, category, server_name, cache_file="sources/video-page/videos_cache.json"
):
    """
    Open the anime episode page and extract the iframe's src for the specified server under a given category.

    :param url: URL of the anime episode page.
    :param category: Category type ('sub' or 'dub').
    :param server_name: The server name to select (e.g., 'VidPlay', 'MyCloud').
    :param cache_file: JSON file to cache results.
    :return: iframe src URL if found, otherwise None.
    """
    # Extract anime and episode info from the URL
    anime_name, episode_name = extract_anime_and_episode(url)

    # Load cache
    cache = load_cache(cache_file)
    cache_key = f"{anime_name}|{episode_name}|{category}|{server_name}"

    if cache_key in cache:
        iframe_src = cache[cache_key]
        print(
            f"Cache hit! Found iframe src for '{anime_name}' - '{episode_name}' in category '{category}' with server '{server_name}': {iframe_src}"
        )
        return iframe_src

    print("Cache miss. Fetching iframe src...")

    # Set up undetected Chrome options
    chrome_options = uc.options.ChromeOptions()
    chrome_options.add_argument("--disable-gpu")
    # Uncomment the next line if you want to run in headless mode
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--blink-settings=imagesEnabled=false")
    chrome_options.add_argument("--window-size=1920x1080")

    # Initialize undetected Chrome driver
    driver = uc.Chrome(options=chrome_options)

    try:
        driver.get(url)
        wait = WebDriverWait(driver, 20)

        # Wait for the server-wrapper elements to load
        server_wrappers = wait.until(
            EC.presence_of_all_elements_located((By.CLASS_NAME, "server-wrapper"))
        )
        print(f"Found {len(server_wrappers)} server-wrapper elements.")

        target_server = None

        # Loop through each server-wrapper
        for wrapper in server_wrappers:
            try:
                # Find category elements matching the specified category (sub/dub)
                category_elements = wrapper.find_elements(
                    By.CSS_SELECTOR, f"div.server-type[data-type='{category}']"
                )
                print(
                    f"Found {len(category_elements)} category elements matching '{category}'."
                )

                for category_element in category_elements:
                    # Look for the server by its name within the current category element
                    server_list = category_element.find_elements(
                        By.CSS_SELECTOR, "div.server"
                    )
                    for server in server_list:
                        server_name_element = server.find_element(By.TAG_NAME, "span")
                        if server_name_element.text.strip() == server_name:
                            target_server = server
                            print(f"Found the server: {server_name}")
                            break
                    if target_server:
                        break
                if target_server:
                    break

            except Exception as e:
                print(f"Error processing a server-wrapper: {e}")
                continue

        if target_server is None:
            raise Exception(
                f"Server '{server_name}' not found in category '{category}'."
            )

        # Click the target server
        driver.execute_script("arguments[0].click();", target_server)
        print(f"Clicked on server '{server_name}'. Waiting for iframe...")

        # Wait for the iframe to appear and fetch its src attribute
        iframe = wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div#player iframe"))
        )
        iframe_src = iframe.get_attribute("src")
        print(f"Iframe src found: {iframe_src}")

        # Cache the result and save it
        cache[cache_key] = iframe_src
        save_cache(cache, cache_file)

        # Optional delay (if needed)
        time.sleep(2)
        return iframe_src

    except Exception as e:
        print(f"Error: {e}")
        return None

    finally:
        driver.quit()


# Prevent driver quit issues
uc.Chrome.__del__ = lambda self: None


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
    base_filename = get_base_filename(url)

    if base_filename in INVALID_PATHS:
        print(f"Skipping fetch for invalid path: {base_filename}")
        return
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
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return {"error": "Invalid anime page or file does not exist."}
    
    with open(file_path, "r", encoding="utf-8") as file:
        soup = BeautifulSoup(file, "lxml")

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
        soup.select_one("#ani_detail .film-description .text").decode_contents().strip()
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
            va_name = (
                va_info.select_one("h4.pi-name a").text.strip()
                if va_info.select_one("h4.pi-name a")
                else "Unknown"
            )
            va_img = (
                va_info.select_one("a.pi-avatar img")["data-src"]
                if va_info.select_one("a.pi-avatar img")
                else ""
            )
            va_nationality = (
                va_info.select_one("span.pi-cast").text.strip()
                if va_info.select_one("span.pi-cast")
                else "Unknown"
            )
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
    html_file_path = os.path.join(
        "sources", "detail-page", f"kaidoto-detail-page-{base_filename}.html"
    )
    json_file_path = os.path.join(
        "sources", "detail-page", f"kaidoto-detail-page-{base_filename}.json"
    )

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
