import requests

def get_manga_id(title="Solo Leveling"):
    response = requests.get(
        "https://api.mangadex.org/manga",
        params={"title": title, "limit": 1}
    )
    response.raise_for_status()
    data = response.json()
    if not data["data"]:
        raise Exception("Manga not found")
    return data["data"][0]["id"]

def get_latest_chapter_id(manga_id):
    response = requests.get(
        "https://api.mangadex.org/chapter",
        params={
            "manga": manga_id,
            "translatedLanguage[]": "en",
            "order[chapter]": "desc",
            "limit": 1
        }
    )
    response.raise_for_status()
    chapters = response.json()["data"]
    if not chapters:
        raise Exception("No English chapters found")
    return chapters[0]["id"]

def get_chapter_images(chapter_id):
    response = requests.get(f"https://api.mangadex.org/at-home/server/{chapter_id}")
    response.raise_for_status()
    data = response.json()
    base_url = data["baseUrl"]
    hash_code = data["chapter"]["hash"]
    image_filenames = data["chapter"]["data"]
    return [f"{base_url}/data/{hash_code}/{filename}" for filename in image_filenames]

def fetch_latest_solo_leveling_images():
    try:
        manga_id = get_manga_id("Solo Leveling")
        latest_chapter_id = get_latest_chapter_id(manga_id)
        image_urls = get_chapter_images(latest_chapter_id)
        print(f"Found {len(image_urls)} pages in the latest chapter:")
        for url in image_urls:
            print(url)
    except Exception as e:
        print(f"❌ Error: {e}")

# Run it
fetch_latest_solo_leveling_images()
