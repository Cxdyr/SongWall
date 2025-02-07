import random
import string
from flask_login import current_user
from sqlalchemy import func
from app.songwall_search import search_songs
from app.models import Follow, Post, User, db, Rating, Song  
from sqlalchemy.orm import joinedload
from sqlalchemy.exc import IntegrityError
from faker import Faker
from app.api_auth import get_access_token

fake = Faker() #for admin panel simulation
#------------------GENERAL FUNCTIONS ---------------------

#User ratings by user id, used for profile view and view/username 
def get_user_ratings(user_id):
    """
    Fetch all ratings for a given user, sorted by highest rating first.
    
    :param user_id: The ID of the user whose ratings are being fetched.
    :return: A list of Rating objects joined with Song data.
    """
    top_ratings = (
        Rating.query
        .filter_by(user_id=user_id)
        .join(Song, Rating.song_id == Song.id)
        .order_by(Rating.rating.desc())
        .limit(10)
        .all()
    )

    recent_ratings = (
        Rating.query
        .filter_by(user_id=user_id)
        .join(Song, Rating.song_id == Song.id)
        .order_by(Rating.time_stamp.desc())
        .all()
    )

    ratings_ct = Rating.query.filter_by(user_id=user_id).count()

    avg_rating = (
        db.session.query(func.avg(Rating.rating)).filter_by(user_id=user_id).scalar()
    )
    if avg_rating is None:
        avg_rating = 0  
    else:
        avg_rating = round(avg_rating, 2)  # 2 decimal


    return top_ratings, recent_ratings, ratings_ct, avg_rating

#Get rating by sporify id, used for deleting ratings from a users rated songs in the settings page
def get_rating_by_spotify_id(user_id, spotify_id):
    """"Gets rating by spotify id used in settings for removal"""
    rating = Rating.query.join(Song).filter(
        Song.spotify_id == spotify_id, Rating.user_id == user_id
    ).first()

    return rating

#Get song by id, used to get full song info by our db song id and avg rating
def get_song_by_id(song_id):
    """Uses my database to get song info and avg rating"""
    song = Song.query.filter_by(id=song_id).first()
    average_rating = db.session.query(func.avg(Rating.rating)).filter(Rating.song_id == song_id).scalar()
    average_rating = round(average_rating, 2)

    return song, average_rating

def get_song_id_meth(song_id):
    """Uses my database to get song info"""
    song = Song.query.filter_by(id=song_id).first()

    return song

#Get song by spotify id, used to get full song info by spotify_id in our db and avg rating
def get_song_by_spotify_id(spotify_id):
    """
    Fetches a song from the database using its Spotify ID.
    
    :param spotify_id: The unique Spotify ID of the song.
    :return: The song object or None if not found and avg rating
    """
    song = get_song_spotify_id_meth(spotify_id)
    song_id = song.id
    average_rating = db.session.query(func.avg(Rating.rating)).filter(Rating.song_id == song_id).scalar()
    return song, average_rating

#Get song by spotify id, used to get full song info by spotify_id in our db
def get_song_spotify_id_meth(spotify_id):
    """
    Fetches a song from the database using its Spotify ID.
    
    :param spotify_id: The unique Spotify ID of the song.
    :return: The song object or None if not found.
    """
    song = Song.query.filter_by(spotify_id=spotify_id).first()
  
    return song

#Add / update rating, used to add ratings to the db by user id, spotify_id, and then adding their inputed comment / rating int
def add_or_update_rating(user_id, username, spotify_id, rating, comment):
    """
    Adds or updates a rating for a song by a specific user.

    :param user_id: The ID of the user rating the song.
    :param spotify_id: The Spotify ID of the song.
    :param rating: The rating value given by the user.
    :param comment: An optional comment for the rating.
    :return: Success message or error.
    """
    song = get_song_spotify_id_meth(spotify_id)

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

#Getting the top rated songs, takes amount usually 9 or 10, and gets the top rated songs and average rating for the index page 
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

#Get recent ratings from any users, used in the dashboard view to populate simple recent ratings and promote community as anyone can see anyones recent ratings
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

#Get recent song ratings by song id specifically, used in the song view page 
def get_song_recent_ratings(song_id):
    """Function to get song info for song page including rating, ratings from users, posts from users eventually (for now not implementing quite yet)"""

    song = db.session.query(Song).filter_by(id = song_id).first()

    if song:
        ratings = db.session.query(Rating).filter_by(song_id=song.id).order_by(Rating.time_stamp.desc()).all()

        return ratings
    
#Get search song recent ratings, used in song view page through the search feature as some songs on here may or may not be in our database so it uses the spotify id versus our db id
def get_search_song_recent_ratings(spotify_id):
    """Function to get song info for song page including rating, ratings from users, posts from users eventually (for now not implementing quite yet)"""

    song = db.session.query(Song).filter_by(spotify_id = spotify_id).first()

    if song:
        ratings = db.session.query(Rating).filter_by(song_id=song.id).order_by(Rating.time_stamp.desc()).all()

        return ratings
    


def add_songs_to_db(songs):
    new_songs = []
    seen_ids = set()  # Track `spotify_id`s already added in this batch
    
    for song_data in songs:
        if song_data['spotify_id'] in seen_ids:  # Skip duplicates in this batch
            continue
        
        existing_song = Song.query.filter_by(spotify_id=song_data['spotify_id']).first()
        
        if not existing_song:
            new_song = Song(
                track_name=song_data['name'],
                artist_name=song_data['artist'],
                album_image=song_data['album_image_url'],
                spotify_url=song_data['spotify_url'],
                spotify_id=song_data['spotify_id'],
                album_name=song_data['album_name'],
                release_date=song_data['release_date']
            )
            new_songs.append(new_song)
            seen_ids.add(song_data['spotify_id'])  # Add to seen list
    
    if new_songs:
        try:
            db.session.bulk_save_objects(new_songs)
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            print("Duplicate song detected, skipping commit.")

    return f"{len(new_songs)} songs added successfully!"




#Get popular songwall songs, takes the amount of popular songs we want, the highest count of ratings in our songwall db are the most popular bad or good and we return these for display
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

def get_recent_ratings_username(username):

    user = db.session.query(User).filter_by(username=username).first()

    if user:
        recent_ratings = (db.session.query(Rating).options(joinedload(Rating.song)).filter_by(user_id=user.id).order_by(Rating.time_stamp.desc()).all())

        return recent_ratings
    else:
        return None

#Get profile info by username, returns the average rating, the user info, the rating amount, and the ratings the user has rated, this is used in the view profile page
def get_profile_info(username):
    """Retreive user profile information for view route"""
    # Query the user by username
    user = db.session.query(User).filter_by(username=username).first()
    
    # Check if the user exists
    if user:
        # Get the ratings for this user (songs they've rated)
        ratings = db.session.query(Rating).filter_by(user_id=user.id).order_by(Rating.rating.desc()).all()
        ratings_ct = Rating.query.filter_by(user_id=user.id).count()
        avg_rating = (
            db.session.query(func.avg(Rating.rating)).filter_by(user_id=user.id).scalar()
        )
        if avg_rating is None:
            avg_rating = 0  
        else:
            avg_rating = round(avg_rating,2)


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
            'ratings': user_ratings,
            'ratings_ct':ratings_ct,
            'avg_rating':avg_rating
        }
    else:
        return None
    

#Gets all of the rated songs by a user in time descening order by user id, this is used in the settings page for deleting songs they dont want rated anymore
def get_rated_songs_by_user(user_id):
    """
    Fetch all songs rated by a specific user.
    Returns a list of (song_id, track_name, artist_name).
    """
    songs = (db.session.query(Song.id, Song.track_name, Song.artist_name, Rating.time_stamp).join(Rating, Rating.song_id == Song.id).filter(Rating.user_id == user_id).order_by(Rating.time_stamp.desc()).all())
    return songs

#Post post, this takes the user id song id and post message and creates a post entry to the database
def add_post(user_id, song_id, post_message):
    """
    Add a new post into the database.
    """
    new_post = Post(
        post_message=post_message,
        user_id=user_id,
        song_id=song_id #this is our reference per say.
    )
    db.session.add(new_post)
    db.session.commit()
    return new_post


#Get recent posts in general, theis gets all recent posts from all users for the post display page
def get_recent_posts(limit=10, offset=0):
    """
    Get recent posts with user and song details, ordered by timestamp.
    Supports pagination via limit and offset.
    """
    posts = (db.session.query(Post).options(joinedload(Post.user), joinedload(Post.song)).order_by(Post.time_stamp.desc()).limit(limit).offset(offset).all())
    return posts


#Get recent posts from specific user by username, this will popular the view_posts/username page where we can see specific users posts.
def get_recent_user_posts(username, limit=10, offset=0):
    """
    Get recent posts with user and song details for a specific user, ordered by timestamp.
    Supports pagination via limit and offset.
    """
    posts = (db.session.query(Post).join(User)  # Join the User table to filter by username
             .filter(User.username == username)  # Filter by the given username
             .options(joinedload(Post.user), joinedload(Post.song))  # Eager loading for user and song
             .order_by(Post.time_stamp.desc())  # Order by timestamp in descending order
             .limit(limit)  # Apply the limit
             .offset(offset)  # Apply the offset
             .all())  # Execute the query and return the results
    
    userinfo = db.session.query(User).filter_by(username=username).first()

    return posts, userinfo


#Function for creating follow relationship for users, this is used in the view_profile/username page so users can follow and updates db accordingly.
def follow_user(followed_id):
    """Adds a follow relationship if not already followed."""
    if followed_id == current_user.id:
        return {"success": False, "message": "You cannot follow yourself!"}

    existing_follow = Follow.query.filter_by(follower_id=current_user.id, followed_id=followed_id).first()

    if existing_follow:
        return {"success": False, "message": "You are already following this user!"}

    new_follow = Follow(follower_id=current_user.id, followed_id=followed_id)
    db.session.add(new_follow)
    db.session.commit()
    return {"success": True, "message": "You are now following this user!"}

#Function for removing the follow relationship
def unfollow_user(followed_id):
    """Removes a follow relationship if it exists."""
    follow = Follow.query.filter_by(follower_id=current_user.id, followed_id=followed_id).first()

    if not follow:
        return {"success": False, "message": "You are not following this user."}

    db.session.delete(follow)
    db.session.commit()
    return {"success": True, "message": "You have unfollowed this user."}


#Get recent follow ratings, this will find follow relationships and populate our follwed ratings caresoul in the dashboard 
def get_recent_follow_ratings(user_id, amount=10):
    """Retrieve the most recent ratings from users that the given user is following."""
    # Get the list of user IDs that the current user is following
    following_ids = (
        db.session.query(Follow.followed_id)
        .filter(Follow.follower_id == user_id)
        .all()
    )
    # Flatten the list of tuples to get just the user ids
    following_ids = [followed_id[0] for followed_id in following_ids]

    # Fetch the recent ratings from followed users
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
        .filter(Rating.user_id.in_(following_ids))  # Filter by followed users
        .order_by(Rating.time_stamp.desc())  # Sort by most recent
        .limit(amount)
        .all()
    )

    return recent_ratings




def get_songs_recent_posts(song_id):
    posts = (
        db.session.query(Post)
        .filter_by(song_id=song_id)
        .order_by(Post.time_stamp)
        .options(joinedload(Post.user), joinedload(Post.song))  # Eager loading
        .limit(6)
        .all()
    )
    return posts


def get_search_song_recent_posts(spotfiy_id):
    song = get_song_spotify_id_meth(spotfiy_id)
    song_id = song.id
    posts = (
        db.session.query(Post)
        .filter_by(song_id=song_id)
        .order_by(Post.time_stamp)
        .options(joinedload(Post.user), joinedload(Post.song))  # Eager loading
        .limit(6)
        .all()
    )
    return posts


#used for display view profile page to only display either the follow or unfollow button
def check_if_following(user_id, followed_id):
    return db.session.query(
        db.session.query(Follow).filter_by(follower_id=user_id, followed_id=followed_id).exists()
    ).scalar()




def get_potential_songs(user_id):
    # Fetch the user's recent rated artists and their associated songs in one query
    recent_rated_artists = (
        db.session.query(Rating)
        .options(joinedload(Rating.song))  # Eager load the song relationship
        .filter(Rating.user_id == user_id)  # Filter by the specific user
        .order_by(Rating.time_stamp.desc())  # Order by most recent ratings
        .limit(6)
        .all()
    )

    # If the user has no rated songs, return None
    if not recent_rated_artists:
        return None

    artists = set()  # Use a set to store unique artist names
    potential_songs = []

    # Extract unique artists from the user's recent ratings
    for rating in recent_rated_artists:
        artist = rating.song.artist_name
        artists.add(artist)

    # Fetch up to 3 songs per artist that the user hasn't rated
    for artist in artists:
        songs_by_artist = (
            db.session.query(Song)
            .filter(Song.artist_name == artist)
            .all()
        )
        songs_added = 0  # Counter to track songs added per artist

        for song in songs_by_artist:
            # Check if the user has already rated this song
            existing_rating = (
                db.session.query(Rating)
                .filter(Rating.user_id == user_id, Rating.song_id == song.id)
                .first()
            )
            if existing_rating is None:  # User hasn't rated this song
                potential_songs.append(song)
                songs_added += 1

            if songs_added >= 3:  # Limit to 3 songs per artist
                break

    return potential_songs
    

#-------------------ADMIN FUNCTIONS ----------------------

def get_all_user_info():
    users = User.query.all() #this method will not require a session to get all information, as an admin panel should
    return users

def get_all_song_info():
    songs = Song.query.all()
    return songs

def get_all_ratings_info():
    ratings = Rating.query.all()
    return ratings

def get_all_posts_info():
    posts = Post.query.all()
    return posts

def random_userinfo(): #Generating fake user info
    username = fake.user_name() + str(random.randint(100,999)) #from the Faker library for all fields
    email = fake.email()
    password = ''.join(random.choices(string.ascii_letters + string.digits, k=12))
    return username, email, password

def create_users(amount):
    users = []
    for _ in range(amount):
        username, email, password = random_userinfo() # collecting our fake user info

        user = User(
            first_name=username,
            username=username,
            email = email
        )
        user.set_password(password)

        db.session.add(user)
        users.append(user)
    
    db.session.commit()


def search_sim(): # Gets access token, then searches through 40 queries updating our database with each iteration so we have songs
    token = get_access_token()
    infos= []
    for _ in range(40):
        song_name = fake.text(max_nb_chars=20).strip() 
        info = search_songs(song_name,token)
        infos.extend(info)
    add_songs_to_db(infos)

def select_random_song(): # randomly selects a song from our existing songs in our database
    song_am = db.session.query(Song).count()
    id = random.randint(1,song_am)
    return id

def rate_song(user, id): # randomly selects a rating, lowest rating being 4 to give average round 6-7 median
    rating = random.randint(4,10)
    existing_rating = Rating.query.filter_by(song_id=id, user_id=user.id).first()

    if existing_rating:
        existing_rating.rating = rating  # Update existing rating
        existing_rating.comment = ""
    else:
        new_rating = Rating(rating=rating, comment="", song_id=id, user_id=user.id, username=user.username)
        db.session.add(new_rating)

    db.session.commit()
    

def rate_sim(): # Looping through each testing user and getting an amount of songs between 6 and 10, and randomly rating each of these songs
    test_users = db.session.query(User).filter(User.email.like('%@example%')).all()
    for user in test_users:
        amount_ratings = random.randint(6,10)
        for _ in range(amount_ratings):
            song = select_random_song()
            rate_song(user, song)



def delete_example_users():
    """
    Deletes all users with '@example' in their email address
    Returns: (success, message)
    """
    try:
        # Find all test users with @example in email
        test_users = User.query.filter(User.email.ilike('%@example%')).all()
        
        if not test_users:
            return True, "No test users found with @example emails"

        # Delete all found users
        for user in test_users:
            db.session.delete(user)
        
        db.session.commit()
        return True, f"Successfully deleted {len(test_users)} test users"
        
    except Exception as e:
        db.session.rollback()
        return False, f"Error deleting test users: {str(e)}"