from datetime import datetime
from flask_login import current_user
from sqlalchemy import func
from models import Post, User, db, Rating, Song  




def get_user_ratings(user_id):
    """
    Fetch all ratings for a given user, sorted by highest rating first.
    
    :param user_id: The ID of the user whose ratings are being fetched.
    :return: A list of Rating objects joined with Song data.
    """
    return (
        Rating.query
        .filter_by(user_id=user_id)
        .join(Song, Rating.song_id == Song.id)
        .order_by(Rating.rating.desc())  # Sort by highest rating first
        .all()
    )



def get_rating_by_spotify_id(user_id, spotify_id):
    """"Gets rating by spotify id used in settings for removal"""
    rating = Rating.query.join(Song).filter(
        Song.spotify_id == spotify_id, Rating.user_id == user_id
    ).first()

    return rating

def get_song_by_id(song_id):
    """Uses my database to get song info"""
    return Song.query.filter_by(id=song_id).first()

def get_song_by_spotify_id(spotify_id):
    """
    Fetches a song from the database using its Spotify ID.
    
    :param spotify_id: The unique Spotify ID of the song.
    :return: The song object or None if not found.
    """
    return Song.query.filter_by(spotify_id=spotify_id).first()




def add_or_update_rating(user_id, username, spotify_id, rating, comment):
    """
    Adds or updates a rating for a song by a specific user.

    :param user_id: The ID of the user rating the song.
    :param spotify_id: The Spotify ID of the song.
    :param rating: The rating value given by the user.
    :param comment: An optional comment for the rating.
    :return: Success message or error.
    """
    song = get_song_by_spotify_id(spotify_id)

    if not song:
        return {"error": "Song not found."}

    existing_rating = Rating.query.filter_by(song_id=song.id, user_id=user_id).first()

    if existing_rating:
        existing_rating.rating = rating  # Update existing rating
        existing_rating.comment = comment
    else:
        new_rating = Rating(rating=rating, comment=comment, song_id=song.id, user_id=user_id, username=username)
        db.session.add(new_rating)

    db.session.commit()
    return {"success": "Rating submitted successfully!"}




def get_top_rated_songs(amount):
    """Retrieve the top-rated songs along with their average rating."""
    top_songs = (
        db.session.query(
            Song.id, 
            Song.track_name, 
            Song.artist_name, 
            Song.album_image, 
            Song.album_name,
            Song.spotify_url,
            func.avg(Rating.rating).label("avg_rating"),
            func.count(Rating.rating).label("rating_count")  
        )
        .join(Rating, Rating.song_id == Song.id)
        .group_by(Song.id)
        .order_by(func.avg(Rating.rating).desc())  # Sort by highest avg rating
        .limit(amount)
        .all()
    )
    
    return top_songs


def get_recent_ratings(amount):
    """Retrieve the most recent ratings from users for the recent ratings tab """
    recent_ratings = (
        db.session.query(
            Song.id, 
            Song.track_name, 
            Song.artist_name, 
            Song.album_image, 
            Song.spotify_url,
            Rating.username,
            Rating.rating,
            Rating.time_stamp
        )
        .join(Rating, Rating.song_id == Song.id)
        .order_by(Rating.time_stamp.desc())  # Sort by highest avg rating
        .limit(amount)
        .all()
    )
    
    return recent_ratings


def get_song_recent_ratings(song_id):
    """Function to get song info for song page including rating, ratings from users, posts from users eventually (for now not implementing quite yet)"""

    song = db.session.query(Song).filter_by(id = song_id).first()

    if song:
        ratings = db.session.query(Rating).filter_by(song_id=song.id).order_by(Rating.time_stamp.desc()).all()

        return ratings
    


def get_search_song_recent_ratings(spotify_id):
    """Function to get song info for song page including rating, ratings from users, posts from users eventually (for now not implementing quite yet)"""

    song = db.session.query(Song).filter_by(spotify_id = spotify_id).first()

    if song:
        ratings = db.session.query(Rating).filter_by(song_id=song.id).order_by(Rating.time_stamp.desc()).all()

        return ratings








def get_popular_songwall_songs(amount):
    """Retreive the most rated - aka popular songs good or bad from our songwall db """
    pop_songs = (
        db.session.query(
            Song.id, 
            Song.track_name, 
            Song.artist_name, 
            Song.album_name,
            Song.album_image, 
            Song.spotify_url,
            func.avg(Rating.rating).label("avg_rating"),
            func.count(Rating.rating).label("rating_count")  
        )
        .join(Rating, Rating.song_id == Song.id)
        .group_by(Song.id)
        .order_by(func.count(Rating.rating).desc())  # Sort by highest avg rating
        .limit(amount)
        .all()
    )
    
    return pop_songs


def get_profile_info(username):
    """Retreive user profile information for view route"""
    # Query the user by username
    user = db.session.query(User).filter_by(username=username).first()
    
    # Check if the user exists
    if user:
        # Get the ratings for this user (songs they've rated)
        ratings = db.session.query(Rating).filter_by(user_id=user.id).order_by(Rating.rating.desc()).all()
        user_ratings = []
        
        # Gather song details for each rating
        for rating in ratings:
            song = db.session.query(Song).filter_by(id=rating.song_id).first()
            if song:
                user_ratings.append({
                    'song': song,
                    'rating': rating.rating,
                    'comment': rating.comment,
                    'album_name': song.album_name
                    
                })
        
        return {
            'user': user,
            'ratings': user_ratings
        }
    else:
        return None




# Function to get recent posts with usernames
def get_recent_posts(limit=10):
    posts = Post.query.order_by(Post.time_stamp.desc()).limit(limit).all()
    # Include the username of the user who posted each message
    posts_with_usernames = []
    for post in posts:
        user = User.query.get(post.user_id)  # Get the user who posted this
        posts_with_usernames.append({
            'post': post,
            'username': user.username if user else "Unknown"
        })
    return posts_with_usernames


# Function to add a new post
def add_post(post_message):
    if post_message:
        new_post = Post(
            post_message=post_message,
            user_id=current_user.id,
            time_stamp=datetime()
        )
        db.session.add(new_post)
        db.session.commit()
        return new_post
    return None


