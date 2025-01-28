import requests
from api_auth import get_access_token

access_token = get_access_token()
# request to search endpoint on spotify given user input
def search_songs(query, access_token):
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
            
            song_info = []  # List to store song details
            for track in tracks:
                # Extract relevant song information
                song_details = {
                    "name": track['name'],
                    "artist": track['artists'][0]['name'],  # First artist
                    "album_name": track['album']['name'],
                    "album_image_url": track['album']['images'][0]['url'] if track['album']['images'] else None,
                    "spotify_url": track['external_urls']['spotify'],
                    "spotify_id": track['id']  # Add the Spotify ID
                }
                song_info.append(song_details)  # Add song details to the list
                
            return song_info  # Return the list of songs as a dictionary
        else:
            print(f"Error searching tracks. Status code: {response.status_code}")
            return []  # Return an empty list if the request fails
    else:
        print("No access token available.")
        return []  # Return an empty list if no access token is available
