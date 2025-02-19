import requests
from app.api_auth import get_access_token
from app.models import Song, db

access_token = get_access_token()
def get_popular_songs_by_genre(genre, access_token):
    """
    Retrieve 30 tracks from Spotify for the given genre, sort by popularity (descending), select the top 10, and add any new songs to the database.
    Returns a list of friendly song dictionaries.
    """

    if not access_token:
        print("No access token available.")
        return []

    search_url = "https://api.spotify.com/v1/search"
    query = f"genre:{genre}"
    params = {
        "q": query,
        "type": "track",
        "limit": 30  # Get the 30 results to choose from
    }
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    
    response = requests.get(search_url, headers=headers, params=params)
    if response.status_code != 200:
        print(f"Error searching tracks. Status code: {response.status_code}")
        return []
    
    data = response.json()
    tracks = data.get('tracks', {}).get('items', [])
    
    # Sort tracks by the popularity field in descending order
    tracks_sorted = sorted(tracks, key=lambda track: track.get('popularity', 0), reverse=True)
    # Select the top 10 tracks
    top_tracks = tracks_sorted[:10]
    
    song_list = []
    for track in top_tracks:
        spotify_id = track.get('id')
        # Check if the song already exists in the database using spotify_id
        existing_song = Song.query.filter_by(spotify_id=spotify_id).first()
        if not existing_song:
            new_song = Song(
                track_name=track.get('name'),
                artist_name=track['artists'][0].get('name') if track.get('artists') else "Unknown Artist",
                spotify_url=track.get('external_urls', {}).get('spotify'),
                album_name=track['album'].get('name') if track.get('album') else "Unknown Album",
                album_image=track['album']['images'][0].get('url') if track.get('album') and track['album'].get('images') else None,
                release_date=track['album'].get('release_date') if track.get('album') else "Unknown",
                spotify_id=spotify_id
            )
            db.session.add(new_song)
            db.session.commit()
            song_data = new_song
        else:
            song_data = existing_song

        # Build a dictionary for the frontend including the DB song id.
        song_details = {
            "id": song_data.id,  # Database ID for linking to view page
            "track_name": song_data.track_name,
            "artist_name": song_data.artist_name,
            "spotify_url": song_data.spotify_url,
            "album_name": song_data.album_name,
            "album_image": song_data.album_image,
            "release_date": song_data.release_date,
            "spotify_id": song_data.spotify_id
        }
        song_list.append(song_details)
    
    return song_list
