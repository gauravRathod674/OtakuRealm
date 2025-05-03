import json
import re
import time
import os
import glob
from urllib.parse import urlparse
from urllib.parse import unquote


from ninja import Router, NinjaAPI, Schema
from django.http import StreamingHttpResponse
from django.http import HttpResponse
from django.db.models import Q
from django.db.models import F
from django.utils import timezone
from typing import Optional

from .pages.login_page import AuthSchema
from .pages.home_page import HomePage
from .pages.login_page import LoginPage
from .pages.anime_detail_page import AnimeDetailPage
from .pages.watch_page import WatchPage
from .pages.watch_page import IframeExtractor
from .pages.search_page import SearchPage
from .pages.manga_home_page import MangaHomePage
from .pages.manga_detail_page import MangaDetailPage
from .pages.read_page import ReadPage
from .pages.chatbot import Chatbot


from pydantic import BaseModel
from typing import List


from api.models import *
from .utils.auth_utils import JWTAuth
from .utils.manga_utils import fetch_manga_metadata
from api.models import *

# Initialize NinjaAPI and a Router for /scrape endpoints
api = NinjaAPI()
router = Router()
# Initialize HomePage and LoginPage instances
home_page = HomePage()
login_page = LoginPage()
manga_home_page = MangaHomePage()
read_page = ReadPage(headless=True)


# ------------------------------
# Home Page Endpoints
# ------------------------------
@api.get("/")
def homepage(request):
    data = home_page.get_homepage_data()  
    return data

@api.get("/personal-recommendations", auth=JWTAuth())
def personal_recommendations(request=None):
    return home_page.set_personal_recommendations(request)

# ------------------------------
# Manga Home Page Endpoint
# ------------------------------
@api.get("/mangahome", auth=JWTAuth(optional=True))
def manga_home(request):
    homepage = MangaHomePage()
    data = homepage.get_homepage_data(request)
    return data


# ------------------------------
# Login Page Endpoints
# ------------------------------
@api.get("/login")
def get_login(request):
    return login_page.get_login(request)


@api.post("/login")
def auth(request, data: AuthSchema):
    return login_page.auth(request, data)


# ------------------------------
# Anime Detail Page Endpoint
# ------------------------------
@router.get("/kaido-detail", response=dict)
def get_kaido_detail(request, pathname: Optional[str] = None):
    """
    If a pathname is provided (e.g., "/attack-on-titan-112"), it is appended to "https://kaido.to"
    and the AnimeDetailPage class handles fetching, parsing, and caching.
    """
    anime_page = AnimeDetailPage()
    data = anime_page.get_detail(pathname)
    return data


# ------------------------------
# Manga Detail Page Endpoint
# ------------------------------
@router.get("/manga-detail/{title}", response=dict)
def get_manga_detail(request, title: str):
    """
    Fetch manga details for a given manga title.
    The title will be taken from the URL (e.g., /manga-detail/SOLO LEVELING).
    """
    manga_page = MangaDetailPage(title)
    data = manga_page.get_manga_data()
    return data


# ------------------------------
# Watch Page Endpoint
# ------------------------------
@api.get("/watch/{slug}/{episode}", response=dict, auth=JWTAuth())
def watch_page_endpoint(request, slug: str, episode: str, title: str, anime_type: str):
    """
    Handle the /watch endpoint with an episode parameter in the URL.
    For example: /watch/dandadan-19319/ep-12?title=Dandadan&anime_type=TV
    """
    response_data = WatchPage.watch(request, slug, episode, title, anime_type)

    # Use .get() to safely retrieve anime_detail
    anime_detail = response_data.get("anime_detail", {})

    if request.user.is_authenticated:
        print("Authenticated user:", request.user, request.user.is_authenticated)

        # If anime_detail is empty, log error and return response_data with an error message
        if not anime_detail:
            print("Error: anime_detail missing in response_data.")
            return {"message": "Error: Anime detail not found.", **response_data}

        # Extract episode number safely
        try:
            current_episode_number = int(episode.replace("ep-", ""))
        except Exception as e:
            print("Error extracting episode number:", e)
            current_episode_number = 1  # fallback

        watch_url = f"/watch/{slug}/{episode}?title={title}&anime_type={anime_type}"

        # Create or get the watch history record
        watch_history_obj, created = WatchHistory.objects.get_or_create(
            user=request.user,
            anime_title=anime_detail.get("title", title),
            episode_number=current_episode_number,
            defaults={
                "cover_image_url": anime_detail.get("poster", ""),
                "content_type": anime_detail.get("film_stats", {}).get("type", ""),
                "watch_url": watch_url,
                "updated_at": timezone.now(),
            },
        )

        try:
            # Add genres to the watch history if available
            genres = anime_detail.get("genres", [])
            genre_objs = []
            for genre_name in genres:
                genre_obj, _ = Genre.objects.get_or_create(name=genre_name)
                genre_objs.append(genre_obj)
            watch_history_obj.genres.set(genre_objs)
            print(watch_history_obj)
        except Exception as e:
            print("Error setting genres:", e)

        print("Watch history (created?):", created)
    else:
        print("You are a guest user.")

    return response_data


# ------------------------------
# Switch Episode Endpoint
# ------------------------------
@api.get("/temp/switch_episode", response=dict, auth=JWTAuth())
def switch_episode(
    request,
    episode_url: Optional[str] = None,
    anime_title: Optional[str] = None,
):
    """
    Switch episode and create a new WatchHistory record
    using anime title from the watch page.
    """
    try:
        if not episode_url or not anime_title:
            return {"message": "Error: Missing episode_url or anime_title."}

        print(f"Switching episode for: {anime_title}, URL: {episode_url}")

        # 1. Fetch new iframe
        new_iframe_src = IframeExtractor.fetch_iframe_src(episode_url, "sub", "Megaplay-1")
        if not new_iframe_src:
            return {"message": "Error: Failed to fetch new iframe src."}

        # 2. Extract episode number
        match = re.search(r"/ep-(\d+)", episode_url)
        episode_number = int(match.group(1)) if match else 1

        # 3. Store watch history
        if request.user.is_authenticated:
            print("Authenticated user:", request.user.username)

            existing = (
                WatchHistory.objects.filter(user=request.user, anime_title=anime_title)
                .order_by("-updated_at")
                .first()
            )

            if existing:
                _, created = WatchHistory.objects.get_or_create(
                    user=request.user,
                    anime_title=anime_title,
                    episode_number=episode_number,
                    defaults={
                        "cover_image_url": existing.cover_image_url,
                        "content_type": existing.content_type,
                        "watch_url": episode_url,
                        "updated_at": timezone.now(),
                    },
                )
                if created:
                    print(
                        f"Watch history created for {anime_title} - Episode {episode_number}"
                    )
                    new_entry = WatchHistory.objects.get(
                        user=request.user,
                        anime_title=anime_title,
                        episode_number=episode_number,
                    )
                    new_entry.genres.set(existing.genres.all())  # Copy genres
                else:
                    print(
                        f"Watch history already exists for {anime_title} - Episode {episode_number}"
                    )

            else:
                return {"message": "Error: No previous watch history for this anime."}
        else:
            print("Guest user attempting episode switch — skipping watch history.")

        return {"iframe_src": new_iframe_src}

    except Exception as e:
        print("Exception occurred in switch_episode:", str(e))
        return {"message": f"Error: {str(e)}"}


# ------------------------------
# Read Page Schemas / Response Models
# ------------------------------
DETAIL_CACHE_DIR = os.path.join("sources", "manga-detail-page")


class ChapterInfo(Schema):
    name: str
    url: str


class ReadPageResponse(Schema):
    images: List[str]
    manga_title: str
    chapter: str
    resolved_path: str
    chapters: List[ChapterInfo]
    cover_image_url: Optional[str] = None
    genres: Optional[List[str]] = None


class ReadPathResponse(Schema):
    success: bool
    read_path: Optional[str] = None
    error: Optional[str] = None
    chapters: Optional[List[dict]] = None
    cover_image_url: Optional[str] = None
    genres: Optional[List[str]] = None


class ReadHistoryRequest(BaseModel):
    manga_title: str
    chapter_name: str
    cover_image_url: Optional[str] = None
    read_url: Optional[str] = None
    total_pages: Optional[int] = None
    last_read_page: Optional[int] = None
    genres: Optional[List[str]] = []

    class Config:
        arbitrary_types_allowed = True


# ------------------------------
# Read Page Endpoints
# ------------------------------


@router.get("/read-page", response=ReadPageResponse)
def read_page_endpoint(request, full_url: str):
    """
    Returns image URLs, manga title, current chapter, resolved path, and chapter list,
    as well as cover image URL and genres (fetched from a cached detail JSON file).
    """
    data = read_page.fetch_images(full_url)

    # Parse the manga slug from the URL.
    parsed = urlparse(unquote(full_url))
    path_parts = parsed.path.strip("/").split("/")
    if len(path_parts) < 2:
        return {**data, "chapters": []}
    slug = path_parts[1]  # e.g., "75577-en-solo-leveling"

    # Derive a title to locate the detail JSON file.
    try:
        title = "_".join(slug.split("-")[2:]).replace(" ", "_")
    except Exception:
        title = slug.replace("-", " ")
    json_file = os.path.join(DETAIL_CACHE_DIR, f"{title}_manga_detail.json")

    cover_image_url = ""
    genres = []
    chapters = []
    if os.path.exists(json_file):
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                detail_data = json.load(f)
            chapters = detail_data.get("chapters", [])
            cover_image_url = detail_data.get("image", {}).get("src", "")
            genres = detail_data.get("genres", [])
        except Exception as e:
            print("⚠️ Error reading manga detail JSON:", e)
    else:
        print("Detail JSON file not found:", json_file)

    return {
        **data,
        "chapters": chapters,
        "cover_image_url": cover_image_url,
        "genres": genres,
    }


@router.get("/get-read-path", response=ReadPathResponse)
def get_read_path(request, title: str):
    """
    Given a manga title, returns the read path for redirecting to /read/<read_path>,
    the chapter list, cover image URL, and genres.
    """
    try:
        dummy_url = f"http://localhost:3000/read/{title.replace(' ', '%20')}"
        result = read_page.fetch_images(dummy_url)
        if "error" in result or not result.get("images"):
            return {"success": False, "error": result.get("error", "No images found.")}
        manga_title = result.get("manga_title", "").strip()
        chapter_name = result.get("chapter", "").strip()
        if not manga_title or not chapter_name:
            return {
                "success": False,
                "error": "Could not extract manga title or chapter.",
            }

        # Search for a matching cached read path.
        read_path = None
        for file in os.listdir(read_page.CACHE_DIR):
            if file.endswith(".json"):
                with open(
                    os.path.join(read_page.CACHE_DIR, file), "r", encoding="utf-8"
                ) as f:
                    data = json.load(f)
                if (
                    data.get("manga_title", "").strip().lower() == manga_title.lower()
                    and data.get("chapter", "").strip().lower() == chapter_name.lower()
                ):
                    read_path = file.replace(".json", "")
                    break

        if not read_path:
            return {"success": False, "error": "Read path not found in cache."}

        # Fetch chapter list, cover image URL, and genres from detail cache.
        slug = title.strip().lower().replace(" ", "_")
        json_files = glob.glob(f"{DETAIL_CACHE_DIR}/*{slug}_manga_detail.json")
        chapter_list = []
        cover_image_url = ""
        genres = []
        if json_files:
            try:
                with open(json_files[0], "r", encoding="utf-8") as f:
                    detail_data = json.load(f)
                chapter_list = detail_data.get("chapters", [])
                cover_image_url = detail_data.get("image", {}).get("src", "")
                genres = detail_data.get("genres", [])
            except Exception as e:
                print("⚠️ Failed to load detail JSON:", e)

        return {
            "success": True,
            "read_path": read_path,
            "chapters": chapter_list,
            "cover_image_url": cover_image_url,
            "genres": genres,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


auth_router = Router(auth=JWTAuth())


@auth_router.post("/read-history")
def create_read_history(request, history: ReadHistoryRequest):
    """
    Store/update user's manga read history.
    """

    if request.user.is_authenticated:
        user = request.user
        print(f"Authenticated user: {user.username}")
    else:
        user = None
        print("Guest user detected, saving read history without user association.")

    # 🧠 Auto-fill cover and genres if not provided
    if not history.cover_image_url or not history.genres:
        metadata = fetch_manga_metadata(history.manga_title)
        if not history.cover_image_url:
            history.cover_image_url = metadata["cover_image_url"]
        if not history.genres:
            history.genres = metadata["genres"]

    if history.total_pages == 0:
        return {
            "success": False,
            "message": "Total pages is zero, skipping history creation.",
        }

    # 📝 Save or update read history
    read_history, created = ReadHistory.objects.update_or_create(
        user=user,
        manga_title=history.manga_title,
        chapter_name=history.chapter_name,
        defaults={
            "cover_image_url": history.cover_image_url,
            "read_url": history.read_url,
            "total_pages": history.total_pages,
            "last_read_page": history.last_read_page,
        },
    )

    # 🔄 Update genres (many-to-many)
    if history.genres:
        # Step 1: Pre-fetch all existing genres
        genre_names = list(set(history.genres))  # deduplicate
        existing_genres_q = Q()
        for g in genre_names:
            existing_genres_q |= Q(name=g)

        existing_genres = {g.name: g for g in Genre.objects.filter(existing_genres_q)}

        # Step 2: Bulk create any missing genres
        to_create = [Genre(name=g) for g in genre_names if g not in existing_genres]
        if to_create:
            Genre.objects.bulk_create(to_create, ignore_conflicts=True)

        # Step 3: Re-fetch all (to include just-created)
        all_genres = {g.name: g for g in Genre.objects.filter(existing_genres_q)}

        # Step 4: Assign in one `.set()` call (atomic DB write)
        read_history.genres.set([all_genres[g] for g in genre_names])

    read_history.save()

    return {
        "success": True,
        "message": "Read history saved successfully",
        "data": {
            "manga_title": read_history.manga_title,
            "chapter_name": read_history.chapter_name,
            "cover_image_url": read_history.cover_image_url,
            "read_url": read_history.read_url,
            "total_pages": read_history.total_pages,
            "last_read_page": read_history.last_read_page,
            "genres": [genre.name for genre in read_history.genres.all()],
            "user": request.user.username if request.user.is_authenticated else "Guest",
        },
    }


# ------------------------------
# Search Page Endpoint
# ------------------------------
@router.get("/search", response=dict)
def search_page_endpoint(
    request, anime_title: str, applied_filters: Optional[str] = None
):
    """
    Handle the search page endpoint.
    Accepts:
      - anime_title: The title to search.
      - applied_filters: (Optional) A JSON string representing applied filters.
    Returns combined search results (filters and cards).
    """
    filters_dict = {}
    if applied_filters:
        try:
            filters_dict = json.loads(applied_filters)
        except Exception as e:
            return {"message": f"Error parsing applied_filters: {e}"}
    search_page = SearchPage(anime_title, applied_filters=filters_dict, useCache=False)
    results = search_page.get_search_results()
    return results


# ------------------------------
# Chatbot Endpoint
# ------------------------------


class ChatbotInput(Schema):
    message: str


@router.post("/chatbot")
def chatbot_endpoint(request, payload: ChatbotInput):
    """
    POST endpoint that returns the chatbot response all at once.
    """
    bot = Chatbot()
    full_response = bot.get_full_response(payload.message)
    print(full_response)

    return HttpResponse(full_response, content_type="text/plain")


# ------------------------------
# Watch History Endpoints
# ------------------------------


@api.get("/watch_history", auth=JWTAuth(), response=list)
def get_watch_history(request):
    watch_history = (
        WatchHistory.objects.filter(user=request.auth)
        .prefetch_related("genres")  # Efficiently load related genres
        .order_by("-updated_at")
    )

    response = []
    for entry in watch_history:
        response.append(
            {
                "id": entry.id,
                "anime_title": entry.anime_title,
                "episode_number": entry.episode_number,
                "cover_image_url": entry.cover_image_url,
                "watch_url": entry.watch_url,
                "content_type": entry.content_type,
                "updated_at": entry.updated_at,
                "genres": [genre.name for genre in entry.genres.all()],
            }
        )

    return response


@api.delete("temp/watch_history/{id}", auth=JWTAuth(), response=dict)
def delete_watch_history(request, id: int):
    """
    Delete a single watch history entry for the authenticated user.
    """
    try:
        entry = WatchHistory.objects.get(id=id, user=request.auth)
        entry.delete()
        return {"message": "Entry deleted successfully."}
    except WatchHistory.DoesNotExist:
        return {"message": "Entry not found."}


@api.delete("temp/watch_history/clear", auth=JWTAuth(), response=dict)
def clear_watch_history(request, body: Optional[dict] = None):
    """
    Delete all watch history entries for the authenticated user.
    Accepts an optional body to allow Axios to send an empty payload.
    """
    WatchHistory.objects.filter(user=request.auth).delete()
    return {"message": "All watch history cleared."}


# ------------------------------
# Read History Endpoints
# ------------------------------
@api.get("/read_history", auth=JWTAuth(), response=list)
def get_read_history(request):
    read_history = (
        ReadHistory.objects.filter(user=request.auth)
        .prefetch_related("genres")
        .order_by("-updated_at")
    )

    print(f"Found {read_history.count()} entries for {request.user.username}")

    response = []
    for entry in read_history:
        response.append(
            {
                "id": entry.id,
                "manga_title": entry.manga_title,
                "chapter_name": entry.chapter_name,
                "cover_image_url": entry.cover_image_url,
                "read_url": entry.read_url,
                "total_pages": entry.total_pages,
                "last_read_page": entry.last_read_page,
                "updated_at": entry.updated_at,
                "genres": [genre.name for genre in entry.genres.all()],
            }
        )

    return response

delete_item_router = Router()

@delete_item_router.delete("/read_history/{id}", auth=JWTAuth(), response=dict)
def delete_read_history(request, id: int):
    """
    Delete a single watch history entry for the authenticated user.
    """
    try:
        entry = ReadHistory.objects.get(id=id, user=request.auth)
        entry.delete()
        return {"message": "Entry deleted successfully."}
    except WatchHistory.DoesNotExist:
        return {"message": "Entry not found."}

clear_history_router = Router()

@clear_history_router.delete("/read_history/clear", auth=JWTAuth(), response=dict)
def clear_read_history(request, body: Optional[dict] = None):
    """
    Delete all watch history entries for the authenticated user.
    Accepts an optional body to allow Axios to send an empty payload.
    """
    if body is not None:
        # Handle the body if needed
        pass
    ReadHistory.objects.filter(user=request.auth).delete()
    return {"message": "All watch history cleared."}

# ------------------------------
# Continue Reading Endpoints
# ------------------------------

@api.get("/continue_reading", auth=JWTAuth(), response=list)
def get_continue_reading(request):
    continue_reading = (
        ReadHistory.objects.filter(user=request.auth)
        .filter(last_read_page__lt=F('total_pages'))  # Only entries where last_read_page is less than total_pages
        .prefetch_related("genres")
        .order_by("-updated_at")
    )

    print(f"Found {continue_reading.count()} entries for {request.user.username} that are not fully read.")

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
                "updated_at": entry.updated_at,
                "genres": [genre.name for genre in entry.genres.all()],
            }
        )

    return response



api.add_router("/scrape", router)
api.add_router("/auth", auth_router)
api.add_router("/delete_item", delete_item_router)
api.add_router("/clear_history", clear_history_router)


if __name__ == "__main__":
    api.run(host="0.0.0.0", port=8000)
