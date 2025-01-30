import base64
import requests
import os
from datetime import datetime, timedelta

# Spotify API credentials
client_id = os.getenv("SPOTIFY_CLIENT_ID")
client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")

# Global variable to store access token and expiration time
access_token = None
token_expiration = None

# Function to get a new access token from Spotify API
def get_access_token():
    global access_token, token_expiration

    # If the token is expired or doesn't exist, get a new one
    if access_token is None or datetime.now() > token_expiration:
        # Get new token
        auth_url = "https://accounts.spotify.com/api/token"
        auth_header = base64.b64encode(f"{client_id}:{client_secret}".encode("utf-8")).decode("utf-8")
        headers = {
            "Authorization": f"Basic {auth_header}",
            "Content-Type": "application/x-www-form-urlencoded"
        }
        data = {
            "grant_type": "client_credentials"
        }

        response = requests.post(auth_url, headers=headers, data=data)

        if response.status_code == 200:
            # Store the new access token and set expiration time
            access_token = response.json()["access_token"]
            expires_in = response.json()["expires_in"]  # In seconds
            token_expiration = datetime.now() + timedelta(seconds=expires_in)
            print(f"New access token acquired at {datetime.now()}")
        else:
            # If the token request fails, print error and return None
            print("Failed to get access token from Spotify API.")
            return None

    return access_token
