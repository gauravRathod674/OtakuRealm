import requests

def fetch_manga_metadata(title: str) -> dict:
    """
    Fetch cover image and genres for a given manga title using MangaDex API.
    Returns dict with 'cover_image_url' and 'genres' or raises ValueError if not found.
    """
    try:
        response = requests.get(
            "https://api.mangadex.org/manga",
            params={
                "title": title,
                "limit": 1,
                "includes[]": ["cover_art"]
            },
            timeout=5  # fail fast
        )
        response.raise_for_status()
        data = response.json()

        if not data.get("data"):
            raise ValueError("Manga not found.")

        manga = data["data"][0]
        manga_id = manga["id"]
        attributes = manga["attributes"]

        # Get genres
        genres = [
            tag["attributes"]["name"]["en"]
            for tag in attributes["tags"]
            if tag["attributes"]["group"] == "genre"
        ]

        # Get cover image
        cover_filename = None
        for relation in manga["relationships"]:
            if relation["type"] == "cover_art":
                cover_filename = relation["attributes"]["fileName"]
                break

        if not cover_filename:
            raise ValueError("Cover image not found.")

        cover_url = f"https://uploads.mangadex.org/covers/{manga_id}/{cover_filename}"

        return {
            "cover_image_url": cover_url,
            "genres": genres
        }

    except Exception as e:
        print(f"[ERROR] Failed to fetch manga metadata for '{title}': {e}")
        return {
            "cover_image_url": "",
            "genres": []
        }