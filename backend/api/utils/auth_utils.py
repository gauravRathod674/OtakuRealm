from ninja.security import HttpBearer
import jwt
from django.conf import settings
from django.contrib.auth import get_user_model
from ninja.errors import HttpError

User = get_user_model()

class JWTAuth(HttpBearer):
    def __init__(self, optional=False):
        self.optional = optional  # Add optional flag

    def authenticate(self, request, token):
        # print("Received token:", token)  # Log the token received
        try:
            if not token:
                if not self.optional:
                    raise HttpError(401, "Missing token")
                request.user = None  # Explicitly set user to None for guest users
                return None

            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
            # print("Decoded token payload:", payload)
            user_id = payload.get("user_id")
            user = User.objects.get(id=user_id)

            # Attach user to request
            request.user = user
            print(f"Authenticated User: {user}")  # Log authenticated user details
            return user

        except (jwt.ExpiredSignatureError, jwt.DecodeError, User.DoesNotExist) as e:
            if self.optional:
                print("Token invalid but optional=True — skipping auth.")
                request.user = None  # Explicitly set user to None
                return None
            print("Token validation failed:", e)  # Log error
            raise HttpError(401, "Invalid or expired token")

