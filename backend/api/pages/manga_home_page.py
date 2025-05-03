import os
import json
import requests
from bs4 import BeautifulSoup
import re
from collections import Counter
from urllib.parse import urljoin, urlencode
from django.db.models import F
from api.models import ReadHistory


def clean_text(text):
    return " ".join(text.strip().split())

def fetch_latest_chapters(manga_title):
    """
    Search for a manga title on MangaPark and return the latest three valid chapters
    (each a dict with 'name' and 'url') from the first search result.
    """
    base_url = "https://mangapark.io"
    search_url = f"{base_url}/search"
    headers = {"User-Agent": "Mozilla/5.0"}

    try:
        # 1. Search for manga title
        response = requests.get(search_url, params={"word": manga_title}, headers=headers, timeout=10)
        response.raise_for_status()
    except Exception as e:
        print(f"❌ Search request failed: {e}")
        return []

    soup = BeautifulSoup(response.text, "lxml")
    first_card = soup.select_one("div[q\\:key='q4_9']")
    if not first_card:
        print("❌ No manga search result found.")
        return []

    link_tag = first_card.select_one("h3[q\\:key='o2_2'] a[href]")
    if not link_tag:
        print("❌ No manga link found in result card.")
        return []

    detail_url = urljoin(base_url, link_tag["href"])
    print(f"✅ Found manga detail URL: {detail_url}")

    try:
        detail_resp = requests.get(detail_url, headers=headers, timeout=10)
        detail_resp.raise_for_status()
    except Exception as e:
        print(f"❌ Failed to fetch manga detail page: {e}")
        return []

    detail_soup = BeautifulSoup(detail_resp.text, "lxml")
    chapter_list_div = detail_soup.find("div", {"data-name": "chapter-list"})
    if not chapter_list_div:
        print("❌ Chapter list not found.")
        return []

    chapter_data = []
    # Iterate over all links, appending only valid chapters until we have three.
    for link in chapter_list_div.find_all("a", href=True):
        chapter_name = clean_text(link.get_text())
        chapter_url = urljoin(base_url, link["href"])
        if chapter_url.startswith(f"{base_url}/title/"):
            chapter_data.append({"name": chapter_name, "url": chapter_url})
            if len(chapter_data) == 3:
                break

    if len(chapter_data) < 3:
        print("❌ Less than 3 valid chapters found.")
    else:
        print("✅ Latest 3 chapters:")
        for ch in chapter_data:
            print(f"  - {ch['name']} -> {ch['url']}")

    return chapter_data

class MangaHomePage:
    JSON_FILE = "sources/manga-homepage/homepage_data.json"
    HTML_FILE = "sources/manga-homepage/homepage.html"
    REMOTE_HTML_URL = "https://manganow.to/home"
    FILTER_URL       = "https://manganow.to/filter"
    PERSONAL_DIR     = "sources/manga-homepage/personal"

    GENRE_MAPPING = {
        "action": "1", "adventure": "2", "animated": "641", "anime": "375",
        "cartoon": "463", "comedy": "3", "comic": "200", "completed": "326",
        "cooking": "133", "detective": "386", "doujinshi": "534", "drama": "10",
        "ecchi": "41", "fantasy": "17", "gender bender": "89", "harem": "11",
        "historical": "30", "horror": "21", "isekai": "70", "josei": "67",
        "magic": "420", "manga": "137", "manhua": "51", "manhwa": "79",
        "martial arts": "12", "mature": "22", "mecha": "72", "military": "1180",
        "mystery": "44", "one shot": "721", "psychological": "23",
        "reincarnation": "1603", "romance": "13", "school life": "4",
        "sci-fi": "24", "seinen": "25", "shoujo": "33", "shoujo ai": "123",
        "shounen": "5", "shounen ai": "680", "slice of life": "14",
        "smut": "734", "sports": "142", "super power": "28",
        "supernatural": "6", "thriller": "1816", "tragedy": "97",
        "webtoon": "60"
    }

    def extract_image_slider(self, soup):
        slider_data = []
        slider_wrap = soup.find("div", class_="deslide-wrap")
        if slider_wrap:
            slides = slider_wrap.find_all("div", class_="swiper-slide")
            for slide in slides:
                cover_a = slide.find("a", class_="deslide-cover")
                img = cover_a.find("img") if cover_a else None
                image_src = img["src"] if img and img.has_attr("src") else None

                chapter_div = slide.find("div", class_="desi-sub-text")
                chapter = (
                    " ".join(chapter_div.get_text(strip=True).split())
                    if chapter_div
                    else None
                )

                title_div = slide.find("div", class_="desi-head-title")
                title_a = title_div.find("a") if title_div else None
                manga_title = title_a.get_text(strip=True) if title_a else None

                desc_div = slide.find(
                    "div",
                    class_="scd-item",
                    string=lambda s: s and "A brief description" in s,
                )
                if not desc_div:
                    desc_div = slide.find("div", class_="scd-item mb-3")
                description = (
                    " ".join(desc_div.get_text(strip=True).split())
                    if desc_div
                    else None
                )

                genres_div = slide.find("div", class_="scd-genres")
                genres = []
                if genres_div:
                    for a in genres_div.find_all("a"):
                        genre_name = a.get_text(strip=True)
                        genre_url = a.get("href")
                        genres.append({"name": genre_name, "url": genre_url})

                slider_data.append(
                    {
                        "image_src": image_src,
                        "chapter": chapter,
                        "manga_title": manga_title,
                        "description": description,
                        "genres": genres,
                    }
                )
        return slider_data

    def extract_trending(self, soup):
        trending_data = []
        card_no = 0
        trending_section = soup.find("div", id="manga-trending")
        if trending_section:
            items = trending_section.find_all("div", class_="swiper-slide")
            for item in items:
                poster_div = item.find("div", class_="manga-poster")
                img = poster_div.find("img") if poster_div else None
                image_src = img["src"] if img and img.has_attr("src") else None

                mp_desc = (
                    poster_div.find("div", class_="mp-desc") if poster_div else None
                )

                title_tag = (
                    mp_desc.find("p", class_="alias-name mb-2").find("strong")
                    if mp_desc and mp_desc.find("p", class_="alias-name mb-2")
                    else None
                )
                manga_title = title_tag.get_text(strip=True) if title_tag else None

                rating = None
                ps = mp_desc.find_all("p") if mp_desc else []
                if len(ps) >= 2:
                    rating = ps[1].get_text(strip=True)

                chapter = None
                if len(ps) >= 4:
                    chapter_p = ps[3]
                    a = chapter_p.find("a")
                    if a:
                        chapter = " ".join(a.get_text(strip=True).split())

                card_no = card_no + 1

                trending_data.append(
                    {
                        "card_no": card_no,
                        "image_src": image_src,
                        "manga_title": manga_title,
                        "rating": rating,
                        "chapter": chapter,
                    }
                )
        return trending_data

    def extract_genres(self, soup):
        genres_data = []
        # Locate the wrapper containing the genres navigation
        genres_wrap = soup.find("div", class_="c_b-list")
        if genres_wrap:
            # The first row is for featured links (Latest, New, etc.)
            # and the second row contains the genres.
            rows = genres_wrap.find_all("div", class_="cbl-row")
            if len(rows) > 1:
                # Use the second row for genres
                genre_items = rows[1].find_all("div", class_="item")
                for item in genre_items:
                    # Skip any "more" toggle button
                    if "item-more" in item.get("class", []):
                        continue
                    a_tag = item.find("a")
                    if a_tag:
                        genre_name = a_tag.get_text(strip=True)
                        genre_url = a_tag.get("href")
                        genres_data.append({"name": genre_name, "url": genre_url})
        return genres_data

    def extract_recommended(self, soup):
        recommended_data = []
        rec_section = soup.find("div", id="manga-featured")
        if rec_section:
            items = rec_section.find_all("div", class_="swiper-slide")
            for item in items:
                poster_div = item.find("div", class_="manga-poster")
                img = poster_div.find("img") if poster_div else None
                image_src = img["src"] if img and img.has_attr("src") else None

                mp_desc = (
                    poster_div.find("div", class_="mp-desc") if poster_div else None
                )

                title_tag = (
                    mp_desc.find("p", class_="alias-name mb-2").find("strong")
                    if mp_desc and mp_desc.find("p", class_="alias-name mb-2")
                    else None
                )
                manga_title = title_tag.get_text(strip=True) if title_tag else None

                rating = None
                ps = mp_desc.find_all("p") if mp_desc else []
                if len(ps) >= 2:
                    rating = " ".join(ps[1].get_text(strip=True).split())

                chapter = None
                chapter_link = None
                if len(ps) >= 4:
                    chapter_p = ps[3]
                    a = chapter_p.find("a")
                    if a:
                        chapter = " ".join(a.get_text(strip=True).split())
                        chapter_link = a.get("href")

                genres = []
                genres_div = item.find("div", class_="fd-infor")
                if genres_div:
                    for a in genres_div.find_all("a"):
                        genre_name = a.get_text(strip=True)
                        genre_url = a.get("href")
                        genres.append({"name": genre_name, "url": genre_url})

                recommended_data.append(
                    {
                        "image_src": image_src,
                        "manga_title": manga_title,
                        "genres": genres,
                        "rating": rating,
                        "chapter": chapter,
                    }
                )
        return recommended_data

    def extract_latest_update(self, soup):
        """
        Extracts the latest update data from the homepage soup.
        For each manga item in the homepage, this function extracts:
        - Poster image source
        - Manga title
        - Genres
        - Latest three chapters (using fetch_latest_chapters)
        Returns a list of dictionaries with these keys.
        """
        latest_data = []
        latest_section = soup.find("section", class_="block_area block_area_home")
        if latest_section:
            items = latest_section.find_all("div", class_="item")
            for item in items:
                # Extract poster image source.
                poster_a = item.find("a", class_="manga-poster")
                img = poster_a.find("img") if poster_a else None
                image_src = img["src"] if img and img.has_attr("src") else None

                # Extract manga title from the detail section.
                detail_div = item.find("div", class_="manga-detail")
                title_a = (
                    detail_div.find("h3", class_="manga-name").find("a")
                    if detail_div and detail_div.find("h3", class_="manga-name")
                    else None
                )
                manga_title = title_a.get_text(strip=True) if title_a else None

                # Extract genres.
                genres = []
                fd_infor = (
                    detail_div.find("div", class_="fd-infor") if detail_div else None
                )
                if fd_infor:
                    span = fd_infor.find("span", class_="fdi-item fdi-cate")
                    if span:
                        for a in span.find_all("a"):
                            genre_name = a.get_text(strip=True)
                            genre_url = a.get("href")
                            genres.append({"name": genre_name, "url": genre_url})

                # Use the new chapter extraction function.
                latest_chapters = (
                    fetch_latest_chapters(manga_title) if manga_title else []
                )

                latest_data.append(
                    {
                        "image_src": image_src,
                        "manga_title": manga_title,
                        "genres": genres,
                        "chapters": latest_chapters,
                    }
                )
        return latest_data

    def extract_most_viewed(self, soup):
        most_viewed = {"today": [], "week": [], "month": []}
        timeframe_ids = {
            "today": "chart-today",
            "week": "chart-week",
            "month": "chart-month",
        }
        for timeframe, section_id in timeframe_ids.items():
            section = soup.find("div", id=section_id)
            if section:
                ul = section.find("ul", class_="ulclear")
                if ul:
                    li_items = ul.find_all("li", class_="item-top")
                    for li in li_items:
                        poster_a = li.find("a", class_="manga-poster")
                        img = poster_a.find("img") if poster_a else None
                        image_src = img["src"] if img and img.has_attr("src") else None

                        detail_div = li.find("div", class_="manga-detail")
                        title_a = (
                            detail_div.find("h3", class_="manga-name").find("a")
                            if detail_div and detail_div.find("h3", class_="manga-name")
                            else None
                        )
                        manga_title = (
                            " ".join(title_a.get_text(strip=True).split())
                            if title_a
                            else None
                        )

                        genres = []
                        fd_infor = (
                            detail_div.find("div", class_="fd-infor")
                            if detail_div
                            else None
                        )
                        if fd_infor:
                            cate_span = fd_infor.find(
                                "span", class_="fdi-item fdi-cate"
                            )
                            if cate_span:
                                for a in cate_span.find_all("a"):
                                    genre_name = a.get_text(strip=True)
                                    genre_url = a.get("href")
                                    genres.append(
                                        {"name": genre_name, "url": genre_url}
                                    )

                        view_count_span = (
                            fd_infor.find("span", class_="fdi-item fdi-view")
                            if fd_infor
                            else None
                        )
                        view_count = (
                            view_count_span.get_text(strip=True)
                            if view_count_span
                            else None
                        )

                        chapter = None
                        chapter_link = None
                        chapter_span = (
                            fd_infor.find("span", class_="fdi-item fdi-chapter")
                            if fd_infor
                            else None
                        )
                        if chapter_span:
                            a = chapter_span.find("a")
                            if a:
                                chapter = " ".join(a.get_text(strip=True).split())
                                chapter_link = a.get("href")

                        most_viewed[timeframe].append(
                            {
                                "image_src": image_src,
                                "manga_title": manga_title,
                                "genres": genres,
                                "view_count": view_count,
                                "chapter": chapter,
                                "chapter_link": chapter_link,
                            }
                        )
        return most_viewed

    def extract_completed(self, soup):
        completed_data = []
        featured_list = soup.find("div", id="featured-04")
        if featured_list:
            swiper_container = featured_list.find("div", class_="swiper-container")
            if swiper_container:
                swiper_wrapper = swiper_container.find("div", class_="swiper-wrapper")
                if swiper_wrapper:
                    slides = swiper_wrapper.find_all("div", class_="swiper-slide")
                    for slide in slides:
                        mg_item = slide.find("div", class_="mg-item-basic")
                        if not mg_item:
                            continue
                        poster_div = mg_item.find("div", class_="manga-poster")
                        if not poster_div:
                            continue
                        img = poster_div.find("img")
                        image_src = img["src"] if img and img.has_attr("src") else None

                        mp_desc = poster_div.find("div", class_="mp-desc")
                        manga_title = None
                        rating = None
                        chapter = None
                        chapter_link = None
                        if mp_desc:
                            title_p = mp_desc.find("p", class_="alias-name mb-2")
                            if title_p:
                                title_strong = title_p.find("strong")
                                if title_strong:
                                    manga_title = " ".join(
                                        title_strong.get_text(strip=True).split()
                                    )
                            p_tags = mp_desc.find_all("p")
                            for p in p_tags:
                                star_icon = p.find("i", class_="fa-star")
                                if star_icon:
                                    rating = (
                                        star_icon.next_sibling.strip()
                                        if star_icon.next_sibling
                                        else None
                                    )
                                    break
                            for p in p_tags:
                                a = p.find("a", href=True)
                                if a:
                                    chapter = " ".join(a.get_text(strip=True).split())
                                    chapter_link = a.get("href")
                                    break

                        detail_div = mg_item.find("div", class_="manga-detail")
                        if detail_div and not manga_title:
                            title_a = (
                                detail_div.find("h3", class_="manga-name").find("a")
                                if detail_div.find("h3", class_="manga-name")
                                else None
                            )
                            if title_a:
                                manga_title = " ".join(
                                    title_a.get_text(strip=True).split()
                                )

                        genres = []
                        if detail_div:
                            fd_infor = detail_div.find("div", class_="fd-infor")
                            if fd_infor:
                                for a in fd_infor.find_all("a"):
                                    genre_name = " ".join(
                                        a.get_text(strip=True).split()
                                    )
                                    genre_url = a.get("href")
                                    genres.append(
                                        {"name": genre_name, "url": genre_url}
                                    )

                        completed_data.append(
                            {
                                "image_src": image_src,
                                "manga_title": manga_title,
                                "genres": genres,
                                "rating": rating,
                                "chapter": chapter,
                                "chapter_link": chapter_link,
                            }
                        )
        return completed_data
    

    def get_continue_reading_data(self, request):
        continue_reading = (
            ReadHistory.objects.filter(user=request.auth)
            .filter(last_read_page__lt=F('total_pages'))
            .prefetch_related("genres")
            .order_by("-updated_at")
        )

        response = []
        for entry in continue_reading:
            response.append(
                {
                    "id": entry.id,
                    "manga_title": entry.manga_title,
                    "chapter_name": entry.chapter_name,
                    "cover_image_url": entry.cover_image_url,
                    "read_url": entry.read_url,
                    "total_pages": entry.total_pages,
                    "last_read_page": entry.last_read_page,
                    "updated_at": entry.updated_at.isoformat(),
                    "genres": [genre.name for genre in entry.genres.all()],
                }
            )
        return response
    
    def _get_personal_recommendations(self, user, limit=12):
        """
        1) Gather ReadHistory, count top‑3 genres.
        2) Map to genre IDs; build ?sort=most-viewed&genres=…
        3) Fetch & parse filter page, scraping each <div class="item item-spc"> card.
        4) Exclude already read titles; limit to `limit`.
        """
        qs = ReadHistory.objects.filter(user=user).prefetch_related("genres")
        if not qs.exists():
            return []

        # 1) Count top‑3 genres
        genre_counter = Counter()
        for h in qs:
            for g in h.genres.all():
                genre_counter[g.name.strip().lower()] += 1
        top_genres = [name for name, _ in genre_counter.most_common(3)]
        genre_ids  = [self.GENRE_MAPPING[g] for g in top_genres if g in self.GENRE_MAPPING]
        if not genre_ids:
            return []

        # 2) Build filter URL
        params = {
            "sort":   "most-viewed",
            "genres": ",".join(genre_ids),
        }
        url = f"{self.FILTER_URL}?{urlencode(params)}"

        # 3) Fetch & scrape
        try:
            resp = requests.get(url, timeout=5)
            resp.raise_for_status()
        except requests.RequestException:
            return []  # or return stale cache if you prefer

        soup = BeautifulSoup(resp.text, "html.parser")
        cards = soup.select("div.item.item-spc")

        # 4) Parse cards & filter out already read
        # Normalize read titles (case-insensitive)
        read_titles = set(title.strip().lower() for title in qs.values_list("manga_title", flat=True))
        recs = []

        for c in cards:
            a = c.select_one("a.manga-poster")
            if not a:
                continue

            img_tag = a.select_one("img.manga-poster-img")
            cover = img_tag["src"].strip() if img_tag else None

            title_tag = c.select_one("h3.manga-name")
            title = title_tag.get_text(strip=True) if title_tag else None
            if not title or title.strip().lower() in read_titles:
                continue

            genres = [
                span.get_text(strip=True)
                for span in c.select("span.fdi-cate a span")
            ]

            recs.append({
                "title":  title,
                "cover":  cover,
                "genres": genres,
            })

            if len(recs) >= limit:
                break


        return recs

    def get_homepage_data(self, request=None):
        data = None
        # Step 1: Try to load data from JSON file if it exists
        if os.path.exists(self.JSON_FILE):
            with open(self.JSON_FILE, "r", encoding="utf8") as infile:
                data = json.load(infile)
            print("Loaded data from JSON file.")

        # Step 2: If no JSON data, try to load HTML from a local file
        if data is None:
            if os.path.exists(self.HTML_FILE):
                with open(self.HTML_FILE, "r", encoding="utf8") as f:
                    html = f.read()
                print("Loaded HTML from local file.")
            else:
                # Step 3: Fetch HTML from the remote URL if not available locally
                print("HTML file not found locally. Fetching from remote URL...")
                response = requests.get(self.REMOTE_HTML_URL)
                if response.status_code == 200:
                    html = response.text
                    os.makedirs(os.path.dirname(self.HTML_FILE), exist_ok=True)
                    with open(self.HTML_FILE, "w", encoding="utf8") as f:
                        f.write(html)
                    print("Fetched HTML from remote URL and saved locally.")
                else:
                    raise Exception(
                        f"Failed to fetch HTML. Status code: {response.status_code}"
                    )

            soup = BeautifulSoup(html, "html.parser")
            data = {
                "image_slider": self.extract_image_slider(soup),
                "trending": self.extract_trending(soup),
                "recommended": self.extract_recommended(soup),
                "latest_update": self.extract_latest_update(soup),
                "most_viewed": self.extract_most_viewed(soup),
                "completed": self.extract_completed(soup),
                "genres": self.extract_genres(soup),  # Added extraction for genres
            }
            os.makedirs(os.path.dirname(self.JSON_FILE), exist_ok=True)
            with open(self.JSON_FILE, "w", encoding="utf8") as outfile:
                json.dump(data, outfile, indent=4, ensure_ascii=False)
            print(f"Extracted data saved to {self.JSON_FILE}")

        print("Data processing complete.")

        # continue reading 
        if hasattr(request, "auth") and request.auth:
            data["continue_reading"] = self.get_continue_reading_data(request)
            print(self.get_continue_reading_data(request))

            print("[Continue Reading] Authenticated User...")
        else:
            data["continue_reading"] = None
            print("[Continue Reading] Guest User...")


        # Personal Recommendation for manga
        user = getattr(request, "user", None)
        if user and getattr(user, "is_authenticated", False):
            os.makedirs(self.PERSONAL_DIR, exist_ok=True)
            personal_path = os.path.join(self.PERSONAL_DIR, f"{user.username}.json")
            if os.path.exists(personal_path):
                with open(personal_path, "r", encoding="utf8") as pf:
                    recs = json.load(pf)
            else:
                recs = self._get_personal_recommendations(user)
                with open(personal_path, "w", encoding="utf8") as pf:
                    json.dump(recs, pf, indent=4, ensure_ascii=False)

            if recs:
                data["personal_recommendations"] = recs

        return data
