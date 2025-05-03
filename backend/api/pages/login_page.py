import re
import jwt
from datetime import datetime, timedelta
from ninja import Router, Schema
from typing import Optional
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.hashers import make_password
from django.conf import settings
from django.core.files.storage import default_storage
from django.templatetags.static import static

User = get_user_model()
JWT_EXP_DELTA_SECONDS = 86400  # Token valid for 1 day

# Schema for auth
class AuthSchema(Schema):
    action: str  # "login" or "register"
    username: str
    password: str
    email: Optional[str] = None

# Schema for auth response
class AuthResponseSchema(Schema):
    success: bool
    message: str
    token: Optional[str] = None
    profile_photo: Optional[str] = None

# Validators
def is_valid_username(username: str) -> bool:
    return bool(re.fullmatch(r'^\w{5,20}$', username))

def is_valid_password(password: str) -> bool:
    return (
        len(password) >= 8 and
        re.search(r'[A-Z]', password) and
        re.search(r'[a-z]', password) and
        re.search(r'\d', password) and
        re.search(r'[!@#$%^&*(),.?":{}|<>]', password)
    )

def is_valid_email(email: str) -> bool:
    return bool(re.fullmatch(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", email))

# JWT generation
def generate_jwt(user):
    payload = {
        'user_id': user.id,
        'username': user.username,
        'exp': datetime.utcnow() + timedelta(seconds=JWT_EXP_DELTA_SECONDS)
    }
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")
    return token

# Get profile photo URL
def get_profile_photo_url(user):
    if hasattr(user, "userprofile") and user.userprofile.profile_photo:
        return user.userprofile.profile_photo.url  # Uses MEDIA_URL
    return "/media/profile_photos/profile_photo.jpg"



# LoginPage class
class LoginPage:
    def get_login(self, request):
        return {"message": "Login page from backend!"}

    def auth(self, request, data: AuthSchema):
        action = data.action.lower().strip()
        username = data.username.strip()
        password = data.password
        email = data.email.strip() if data.email else None

        if action == "register":
            if not is_valid_username(username):
                return {"success": False, "message": "Username must be 5-20 characters and contain only letters, numbers, and underscores."}
            if not email or not is_valid_email(email):
                return {"success": False, "message": "Please provide a valid email address."}
            if not is_valid_password(password):
                return {"success": False, "message": "Password must be at least 8 characters long and include uppercase, lowercase, digit, and special character."}
            if User.objects.filter(username=username).exists():
                return {"success": False, "message": "Username already exists."}
            try:
                user = User.objects.create(
                    username=username,
                    email=email,
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
                profile_url = get_profile_photo_url(user)
                return {
                    "success": True,
                    "message": "Login successful!",
                    "token": token,
                    "profile_photo": profile_url
                }
            except Exception as e:
                return {"success": False, "message": f"Error generating token: {str(e)}"}
        else:
            return {"success": False, "message": "Invalid action. Use 'login' or 'register'."}
