import os
import json
import re
import requests
from bs4 import BeautifulSoup
from collections import Counter
from api.models import WatchHistory

class HomePage:
    TYPE_MAPPING = {
        "movie":   "1",
        "tv":      "2",
        "ova":     "3",
        "ona":     "4",
        "special": "5",
        "music":   "6",
    }

    GENRE_MAPPING = {
        "action":        "1",
        "adventure":     "2",
        "cars":          "3",
        "comedy":        "4",
        "dementia":      "5",
        "demons":        "6",
        "mystery":       "7",
        "drama":         "8",
        "ecchi":         "9",
        "fantasy":      "10",
        "game":         "11",
        "harem":        "35",
        "historical":   "13",
        "horror":       "14",
        "isekai":       "44",
        "josei":        "43",
        "kids":         "15",
        "magic":        "16",
        "martial arts": "17",
        "mecha":        "18",
        "military":     "38",
        "music":        "19",
        "parody":       "20",
        "police":       "39",
        "psychological":"40",
        "romance":      "22",
        "samurai":      "21",
        "school":       "23",
        "sci‑fi":       "24",
        "seinen":       "42",
        "shoujo":       "25",
        "shoujo ai":    "26",
        "shounen":      "27",
        "shounen ai":   "28",
        "slice of life":"36",
        "space":        "29",
        "sports":       "30",
        "super power":  "31",
        "supernatural": "37",
        "thriller":     "41",
        "vampire":      "32",
    }

    def __init__(self):
        # Define the homepage URL and file paths for caching
        self.homepage_url = "https://kaido.to/home"
        self.html_path = os.path.join("sources", "home-page", "homepage.html")
        self.json_path = os.path.join("sources", "home-page", "homepage.json")
        self.personal_dir = os.path.join("sources", "home-page", "personal")

    def get_homepage_data(self, request=None):
        """
        Returns structured homepage data.
        If a JSON cache exists, load and return it.
        Else, if an HTML cache exists, parse it.
        Otherwise, fetch the HTML from the homepage, save it, parse it,
        cache the parsed data as JSON, and return the result.
        """
        # Load cached JSON data or fetch from HTML
        if os.path.exists(self.json_path):
            with open(self.json_path, "r", encoding="utf-8") as jf:
                data = json.load(jf)
        else:
            if os.path.exists(self.html_path):
                data = self._parse_homepage(self.html_path)
            else:
                try:
                    response = requests.get(self.homepage_url)
                    response.raise_for_status()  # Check if the request was successful
                    os.makedirs(os.path.dirname(self.html_path), exist_ok=True)
                    with open(self.html_path, "w", encoding="utf-8") as html_file:
                        html_file.write(response.text)
                    data = self._parse_homepage(self.html_path)
                except requests.exceptions.RequestException as e:
                    raise Exception("Error fetching homepage data: " + str(e))

            # Cache the parsed data as JSON
            os.makedirs(os.path.dirname(self.json_path), exist_ok=True)
            with open(self.json_path, "w", encoding="utf-8") as jf:
                json.dump(data, jf, indent=4, ensure_ascii=False)

        return data

    def _parse_homepage(self, file_path):
        """Reads the HTML from file_path, parses it with BeautifulSoup, and returns a structured dictionary."""
        with open(file_path, "r", encoding="utf-8") as f:
            html = f.read()
        soup = BeautifulSoup(html, "html.parser")
        data = {
            "image_slider": self._parse_image_slider(soup),
            "trending_anime": self._parse_trending_anime(soup),
            "top_sections": self._parse_top_sections(soup),
            "latest_new_upcoming": self._parse_latest_new_upcoming(soup),
            "genres": self._parse_genres(soup),
            "most_viewed": self._parse_most_viewed(soup),
            # "footer": self._parse_footer(soup)
        }
        return data
    

    def _get_personal_recommendations(self, user):
        """
        1. Load WatchHistory entries; if none, return [].
        2. Count top-3 genre names & top-1 content_type.
        3. Map them using GENRE_MAPPING and TYPE_MAPPING.
        4. Build Kaido.to filter URL and scrape .flw-item cards.
        5. Exclude already watched titles, limit to 10.
        """
        qs = WatchHistory.objects.filter(user=user).prefetch_related("genres")
        if not qs.exists():
            return []

        # 1) Count genres and content types
        genre_counts = Counter()
        type_counts  = Counter()
        for e in qs:
            ct = (e.content_type or "").strip().lower()
            if ct:
                type_counts[ct] += 1
            for g in e.genres.all():
                genre_counts[g.name.strip().lower()] += 1

        # 2) Pick top‑3 genres → IDs
        top_genres = [name for name, _ in genre_counts.most_common(3)]
        genre_ids  = [self.GENRE_MAPPING[g] for g in top_genres if g in self.GENRE_MAPPING]

        # 3) Pick top‑1 content_type → code
        top_type = type_counts.most_common(1)[0][0] if type_counts else None
        type_code = self.TYPE_MAPPING.get(top_type, "2")  # default TV

        # 4) Build filter URL & scrape
        params = {"type": type_code, "sort": "most_watched"}
        if genre_ids:
            params["genres"] = ",".join(genre_ids)
        qs_str = "&".join(f"{k}={v}" for k, v in params.items())
        url    = f"https://kaido.to/filter?{qs_str}"

        resp = requests.get(url, timeout=5)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        # 5) Parse & filter
        recs = []
        cards = soup.select("div.film_list-wrap .flw-item") or soup.select(".flw-item")
        watched_titles = set(WatchHistory.objects.filter(user=user).values_list("anime_title", flat=True))

        for c in cards:
            a = c.select_one("h3.film-name a.dynamic-name")
            if not a:
                continue

            title = a.get_text(strip=True)
            if title in watched_titles:
                continue

            url = a["href"]
            cover_img = c.select_one("img.film-poster-img")
            cover = cover_img.get("data-src") or cover_img.get("src") if cover_img else None

            # Additional metadata
            badge_18 = bool(c.select_one("div.tick-rate"))  # True if 18+ label exists
            subtitle = c.select_one(".tick-sub")
            dub      = c.select_one(".tick-dub")
            eps      = c.select_one(".tick-eps")
            subtitle_text = subtitle.get_text(strip=True) if subtitle else ""
            dub_text      = dub.get_text(strip=True) if dub else ""
            eps_text      = eps.get_text(strip=True) if eps else ""

            type_ = ""
            runtime = ""
            type_elem = c.select("span.fdi-item")
            if type_elem:
                type_ = type_elem[0].get_text(strip=True)
                if len(type_elem) > 1:
                    runtime = type_elem[1].get_text(strip=True)

            recs.append({
                "title": title,
                "url": url,
                "cover": cover,
                "is_adult": badge_18,
                "subtitle_episodes": subtitle_text,
                "dubbing_episodes": dub_text,
                "total_episodes": eps_text,
                "type": type_,
                "runtime": runtime
            })

            if len(recs) >= 12:
                break

        return recs
    
    def set_personal_recommendations(self,request=None):
        data = []
          # Personal recommendations for authenticated users
        if request and hasattr(request, "user") and request.user.is_authenticated:
            print("Authenticated user")
            user = request.user
            os.makedirs(self.personal_dir, exist_ok=True)
            personal_path = os.path.join(self.personal_dir, f"{user.username}.json")

            if os.path.exists(personal_path):
                with open(personal_path, "r", encoding="utf-8") as pf:
                    recs = json.load(pf)
            else:
                recs = self._get_personal_recommendations(user)
                # Cache recommendations even if empty to avoid recomputing every time
                with open(personal_path, "w", encoding="utf-8") as pf:
                    json.dump(recs, pf, indent=4, ensure_ascii=False)

            if recs:
               return recs
        else:
            print("Guest")
            return []

    def _parse_image_slider(self, soup):
        slider = soup.select_one("div.deslide-wrap #slider")
        slides = []
        if slider:
            for slide in slider.select(".swiper-slide"):
                spotlight = slide.select_one(".deslide-item .deslide-item-content .desi-sub-text")
                spotlight_text = spotlight.get_text(strip=True) if spotlight else ""
                title_elem = slide.select_one(".deslide-item .deslide-item-content .desi-head-title")
                title = title_elem.get_text(strip=True) if title_elem else ""
                poster_elem = slide.select_one(".deslide-item .deslide-cover .deslide-cover-img img")
                poster = poster_elem.get("data-src", poster_elem.get("src", "")) if poster_elem else ""
                detail_link = slide.select_one(".desi-buttons a.btn-secondary")
                detail_url = detail_link.get("href", "") if detail_link else ""
                description_elem = slide.select_one(".deslide-item .deslide-item-content .desi-description")
                description = description_elem.get_text(strip=True) if description_elem else ""
                stats = {}
                tick_div = slide.select_one(".deslide-item .deslide-item-content .sc-detail .tick")
                if tick_div:
                    tick_sub = tick_div.select_one(".tick-item.tick-sub")
                    tick_dub = tick_div.select_one(".tick-item.tick-dub")
                    tick_eps = tick_div.select_one(".tick-item.tick-eps")
                    stats["subtitles"] = tick_sub.get_text(strip=True) if tick_sub else ""
                    stats["dubbing"] = tick_dub.get_text(strip=True) if tick_dub else ""
                    stats["episodes"] = tick_eps.get_text(strip=True) if tick_eps else ""
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

    def _parse_trending_anime(self, soup):
        trending = []
        trending_section = soup.select_one("#anime-trending")
        if trending_section:
            for item in trending_section.select(".swiper-slide.item-qtip"):
                num_elem = item.select_one(".number span")
                number = num_elem.get_text(strip=True) if num_elem else ""
                title_elem = item.select_one(".film-title.dynamic-name")
                title = title_elem.get_text(strip=True) if title_elem else ""
                detail_link = item.select_one("a.film-poster")
                url = detail_link.get("href", "") if detail_link else ""
                img_elem = item.select_one("a.film-poster img")
                poster = img_elem.get("data-src", img_elem.get("src", "")) if img_elem else ""
                trending.append({
                    "number": number,
                    "title": title,
                    "poster": poster,
                    "url": url
                })
        return trending

    def _parse_top_sections(self, soup):
        anime_data = []
        sections = soup.find_all("div", class_="col-xl-3 col-lg-6 col-md-6 col-sm-12 col-xs-12")
        for section in sections:
            header_elem = section.find("div", class_="anif-block-header")
            section_header = header_elem.text.strip() if header_elem else ""
            anime_list = []
            anime_items = section.find_all("li")
            for item in anime_items:
                img_tag = item.find("img", class_="film-poster-img")
                image_url = img_tag["data-src"] if img_tag and "data-src" in img_tag.attrs else None
                title_tag = item.find("a", class_="dynamic-name")
                title = title_tag["title"] if title_tag and "title" in title_tag.attrs else None
                url = title_tag["href"] if title_tag and "href" in title_tag.attrs else None
                film_name = title_tag.text.strip() if title_tag else None
                tick_sub = item.find("div", class_="tick-sub")
                tick_sub_text = tick_sub.text.strip() if tick_sub else None
                tick_dub = item.find("div", class_="tick-dub")
                tick_dub_text = tick_dub.text.strip() if tick_dub else None
                tick_eps = item.find("div", class_="tick-eps")
                episode_text = tick_eps.text.strip() if tick_eps else None
                tick_type = item.find("div", class_="tick")
                type_text = tick_type.text.strip() if tick_type else None
                if type_text:
                    type_text = re.sub(r'[^a-zA-Z]', '', type_text)
                anime_dict = {
                    "image_url": image_url,
                    "anime_title": film_name,
                    "url": url,
                    "subtitle": tick_sub_text,
                    "dubbing": tick_dub_text,
                    "episode": episode_text,
                    "type": type_text
                }
                anime_list.append(anime_dict)
            view_more_elem = section.select("div.more a")
            view_more = view_more_elem[0]["href"] if view_more_elem else None
            anime_list.append({"view_more": view_more})
            anime_data.append({
                "section": section_header,
                "anime": anime_list
            })
        return anime_data

    def _parse_latest_new_upcoming(self, soup):
        sections = soup.find_all('section', class_='block_area block_area_home')
        anime_data = []
        for section in sections:
            heading_tag = section.find('h2', class_='cat-heading')
            heading = heading_tag.text.strip() if heading_tag else "Unknown Section"
            view_more_elem = section.find('div', class_='block_area-header')
            view_more_url = ""
            if view_more_elem:
                view_more_link = view_more_elem.find('a', class_='btn')
                if view_more_link:
                    view_more_url = view_more_link['href']
            anime_items = section.find_all('div', class_='flw-item')
            anime_list = [{'view_more': view_more_url}]
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
            anime_data.append({
                'section': heading,
                'anime': anime_list,
            })
        return anime_data

    def _parse_genres(self, soup):
        genres = []
        for li in soup.select("ul.sidebar_menu-list li"):
            a = li.select_one("a.nav-link")
            if a:
                name = a.get_text(strip=True)
                url = a.get("href", "")
                genres.append({"name": name, "url": url})
        return genres

    def _parse_most_viewed(self, soup):
        categories = [
            ("Today", "top-viewed-day"),
            ("Week", "top-viewed-week"),
            ("Month", "top-viewed-month"),
        ]
        most_viewed = []
        for category, tab_id in categories:
            data = []
            tab_content = soup.find("div", id=tab_id)
            if tab_content:
                li_items = tab_content.find("ul", class_="ulclear").find_all("li")
                for li in li_items:
                    rank_elem = li.find("div", class_="film-number")
                    rank = rank_elem.get_text(strip=True) if rank_elem else ""
                    poster_elem = li.find("div", class_="film-poster")
                    img_tag = poster_elem.find("img") if poster_elem else None
                    image_url = img_tag.get("data-src") or img_tag.get("src") if img_tag else ""
                    title_elem = li.find("h3", class_="film-name")
                    title = ""
                    url = ""
                    if title_elem:
                        a_tag = title_elem.find("a")
                        if a_tag:
                            title = a_tag.get_text(strip=True)
                            url = a_tag.get("href", "")
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

    def _parse_footer(self, soup):
        footer_links = []
        for link in soup.select('.az-list li a'):
            footer_links.append({
                'text': link.get_text(strip=True),
                'url': link['href']
            })
        return footer_links

# Uncomment the block below for standalone testing:
# if __name__ == "__main__":
#     hp = HomePage()
#     data = hp.get_homepage_data()
#     print(json.dumps(data, indent=4, ensure_ascii=False))
