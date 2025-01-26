import requests
import base64
import os
import sys
from dotenv import load_dotenv


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

# request to search endpoint on spotify given user input
def search_songs(query):
    access_token = get_access_token()
    if access_token:
        search_url = "https://api.spotify.com/v1/search"
        params = {
            "q": query,
            "type": "track",
            "limit": 5
        }
        headers = {
            "Authorization": f"Bearer {access_token}"
        }
        response = requests.get(search_url, headers=headers, params=params)
        
        if response.status_code == 200:
            data = response.json()
            tracks = data['tracks']['items']
            for track in tracks:
                print(f"Track: {track['name']} by {track['artists'][0]['name']}") # TO BE CHANGED obviously through json info not printing
        else:
            print(f"Error searching tracks. Status code: {response.status_code}")
    else:
        print("No access token available.")

# testing purposes for now
if __name__ == "__main__":
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])  
        print(f"Searching for: {query}") 
        search_songs(query)
    else:
        print("Please provide your query")
