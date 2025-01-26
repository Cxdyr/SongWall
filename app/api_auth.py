import base64
import requests
import os


# cliend id and secret, TOP SECRET INFO RIGHT HERE !!!
client_id = os.getenv("SPOTIFY_CLIENT_ID")
client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")

# Getting access token off of my app client id and secret
def get_access_token():
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
        access_token = response.json()["access_token"]
        return access_token
    else:
        print("Failed to get access token.")
        return None