from django.db import models
from django.contrib.auth.models import User

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    profile_photo = models.ImageField(
        upload_to="profile_photos/",
        null=True,
        blank=True,
        default="profile_photos/profile_photo.jpg",
    )

    def __str__(self):
        return self.user.username
    
class Genre(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class WatchHistory(models.Model):
    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="watch_history")
    anime_title = models.CharField(max_length=255)
    episode_number = models.PositiveIntegerField()
    cover_image_url = models.URLField(max_length=500, null=True, blank=True, help_text="URL to the anime cover image")
    watch_url = models.URLField(max_length=500, null=True, blank=True, help_text="URL to the episode being watched")

    content_type = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        help_text="Type of content: TV, Movie, OVA, Special, etc."
    )

    genres = models.ManyToManyField(Genre, related_name="watch_histories", blank=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'anime_title', 'episode_number')

    def __str__(self):
        return f"{self.user.username} - {self.anime_title} Ep{self.episode_number}"
  
class ReadHistory(models.Model):
    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="read_history")
    manga_title = models.CharField(max_length=255)
    chapter_name = models.CharField(max_length=255)
    cover_image_url = models.URLField(
        max_length=500,
        null=True,
        blank=True,
        help_text="URL to the manga cover image"
    )
    read_url = models.URLField(
        max_length=500,
        null=True,
        blank=True,
        help_text="URL to the manga chapter being read"
    )
    total_pages = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Total number of pages in the chapter"
    )
    last_read_page = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Last page the user read"
    )

    genres = models.ManyToManyField(Genre, related_name="read_histories", blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'manga_title', 'chapter_name')

    def __str__(self):
        return f"{self.user.username} - {self.manga_title} {self.chapter_name}"
