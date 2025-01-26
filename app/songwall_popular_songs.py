from api_auth import get_access_token
import requests
import json



def get_popular_songs():
    access_token = get_access_token()
    playlist_id = "5ABHKGoOzxkaa28ttQV9sE"   # This is the ONLY playlist i could find in my brief low effort search for public access playlists the get endpoint has access to, its the top 100 most streamed all time songs spotify
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
            result = []

            for track in tracks:
                track_name = track['track']['name']
                artist_name = track['track']['artists'][0]['name']
                album_image = track['track']['album']['images'][0]['url'] if track['track']['album']['images'] else None
                
                # add track details to the result
                result.append({
                    "track_name": track_name,
                    "artist_name": artist_name,
                    "album_image": album_image
                })

            # 
            return json.dumps(result, indent=4)
        else:
            print(f"Error fetching playlist tracks. Status code: {response.status_code}")
            print(f"Response: {response.text}")

# testing purposes for now
if __name__ == "__main__":
    tracks_json = get_popular_songs(playlist_id)
    if tracks_json:
        print(tracks_json)