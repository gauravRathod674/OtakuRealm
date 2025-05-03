import os
import sys

# Get absolute path to this file and step up to the root of the project
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
# PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, "../../"))
# sys.path.insert(0, PROJECT_ROOT)

# Set Django settings module
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.backend.settings")

import django
django.setup()

# ✅ Test if Django is working
from django.conf import settings
print("Django loaded:", settings.SECRET_KEY)

# ✅ Your actual import
from api.pages.anime_detail_page import AnimeDetailPage

if __name__ == "__main__":
    anime = AnimeDetailPage()
    data = anime.get_detail("/can-a-boy-and-girl-friendship-hold-up-no-it-cant-19549")
    print(data)
