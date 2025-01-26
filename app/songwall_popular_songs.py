from api_auth import get_access_token
import requests


playlist_id = "5ABHKGoOzxkaa28ttQV9sE"   # This is the ONLY playlist i could find in my brief low effort search for public access playlists the get endpoint has access to, its the top 100 most streamed all time songs spotify
def get_popular_songs(playlist_id):
    access_token = get_access_token()
    if access_token:
        search_url = f"https://api.spotify.com/v1/playlists/{playlist_id}/tracks"
        headers = {
            "Authorization": f"Bearer {access_token}"
        }
        params = {
            "limit": 10
        }
        response = requests.get(search_url, headers=headers, params=params)

        if response.status_code==200:
            data = response.json()
            tracks = data['items']
            for idx, track in enumerate(tracks, start=1):
                track_name = track['track']['name']
                artist_name = track['track']['artists'][0]['name']
                print(f"{idx}. {track_name} by {artist_name}")
        else:
            print(f"Error fetching playlist tracks. Status code: {response.status_code}")
            print(f"Response: {response.text}")

# testing purposes for now
if __name__ == "__main__":
    get_popular_songs(playlist_id)
