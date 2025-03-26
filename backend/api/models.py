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
