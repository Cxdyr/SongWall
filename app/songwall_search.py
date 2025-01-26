import requests
import sys
from api_auth import get_access_token

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
            #return tracks
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
