from flask import Flask, app, current_app, jsonify, render_template, request, redirect, url_for, flash, g
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from app.api_auth import get_access_token
from app.genre_search import get_popular_songs_by_genre
from app.models import Post, Rating, Song, User, db
from app.songwall_recommendations import get_user_recommendations, update_user_recommendations
from app.songwall_search import search_songs
from app.db_functions import (
    add_or_update_rating, add_post, add_songs_to_db, authenticate_user, check_if_following, create_user, create_users, delete_example_users, delete_user_by_id,
    follow_user, get_all_posts_info, get_all_ratings_info, get_all_song_info, get_all_user_info, get_most_viewed_songs_last_30_days,
    get_popular_songwall_songs, get_potential_songs, get_profile_info, get_rated_songs_by_user, get_recent_follow_ratings,
    get_recent_posts, get_recent_ratings_username, get_recent_user_posts, get_search_song_recent_posts,
    get_search_song_recent_ratings, get_song_by_id, get_song_by_spotify_id, get_song_id_meth,
    get_song_recent_ratings, get_song_spotify_id_meth, get_songs_recent_posts, get_top_rated_songs,
    get_user_ratings, get_recent_ratings, pin_or_unpin_rating, rate_sim, record_song_view, search_sim, unfollow_user
)
from app.index_song_info import get_cached_songs, initialize_cache, update_cache_if_needed
from flask_migrate import Migrate
import os

# Create the Flask app and configure it.
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'default_secret_key')
database_url = os.environ.get('DATABASE_URL', 'sqlite:///songwall.db')
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)
app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
migrate = Migrate(app,db)

login_manager = LoginManager(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    with db.session() as session:
        return session.get(User, int(user_id))

@app.before_request
def check_token():
    """Ensures a valid access token is available for API requests."""
    global access_token
    if 'access_token' not in g or access_token is None:
        access_token = get_access_token()
        g.access_token = access_token  # Store token in request context
    if not access_token:
        return redirect(url_for('songwall_down'))

@app.route('/songwall_down')
def songwall_down():
    return render_template('songwall_down.html')


#Home page
@app.route('/')
def index():
    initialize_cache(current_app) 
    update_cache_if_needed(current_app)

    recent_songs, top_rated_songs = get_cached_songs()
    return render_template('index.html', recent_songs=recent_songs, top_rated_songs=top_rated_songs)

#Blog page
@app.route('/blog')
def blog():
    return render_template('blog.html')

#Register page
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email'].strip().lower()
        username = request.form['username'].strip()
        password = request.form['password']
        first_name = request.form['first_name']
        
        if len(password)<5:
            flash('Password must be more than 5 characters', 'error')
            return redirect(url_for('register'))
        
        if len(username)>9:
            flash('Username cannot exceed 9 characters', 'error')
            return redirect(url_for('register'))
        
        success, result = create_user(email, username, password, first_name)  # Register/Create user function - adds to db 
        if not success:
            flash(result, 'error')
            return redirect(url_for('register'))
        
        flash('Account created successfully! Please login.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')

#Login page
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email'].lower()
        password = request.form['password']

        success, result = authenticate_user(email, password)  #Login/Auth user function 
        if success:
            login_user(result)
            return redirect(url_for('dashboard'))
        else:
            flash(result, 'error')
    
    return render_template('login.html')

#Logout route
@app.route('/logout')
def logout():
    logout_user()
    flash('You have been logged out successfully!', 'info')
    return redirect(url_for('login'))

#About us page
@app.route('/about')
def about():
    return render_template('about.html')

#Privacy page
@app.route('/privacy')
def privacy():
    return render_template('privacy.html')

#Terms page
@app.route('/terms')
def terms():
    return render_template('terms.html')

#Route for grabbing the popular songs by genre to prevent page reload
@app.route('/genre_songs/<genre>')
@login_required
def genre_songs_ajax(genre):
    # Get the genre songs (30 results sorted, top 10 selected, with DB check/insert)
    songs = get_popular_songs_by_genre(genre, g.access_token)
    return jsonify(songs=songs)

# Logged in home page
@app.route('/dashboard', methods=['GET', 'POST'])
@login_required
def dashboard():
    # updates the cache if needed, but wont update the full userbase recommendations
    update_cache_if_needed(app)
    
    # This ensures the current user's recommendations stay fresh with their latest activity
    recommendations = update_user_recommendations(current_user.id, limit=10)
    followed_ratings = get_recent_follow_ratings(current_user.id)
    most_viewed_songs = get_most_viewed_songs_last_30_days()
    recent_posts = get_recent_posts(3, 0)  # getting the 4 recent posts with offset 0
    user_songs = get_rated_songs_by_user(current_user.id)  # getting the rated songs for the user for posting potential 
    
    # Get selected genre from query parameter; default to "pop"
    selected_genre = request.args.get('genre', 'pop')
    # Retrieve popular songs for the selected genre
    genre_songs = get_popular_songs_by_genre(selected_genre, g.access_token)
    
    if request.method == 'POST':
        song_id = request.form.get('song_id')
        post_message = request.form.get('post_message')
        if song_id and post_message:
            add_post(current_user.id, song_id, post_message)
            return redirect(url_for('dashboard'))
    
    return render_template(
        'dashboard.html',
        followed_ratings=followed_ratings,
        recent_posts=recent_posts,
        user_songs=user_songs,
        top_songs=most_viewed_songs,
        selected_genre=selected_genre,
        genre_songs=genre_songs,
        recommendations=recommendations
    )

# Route to explicitly refresh recommendations (optional for users who want to force refresh)
@app.route('/refresh-recommendations')
@login_required
def refresh_recommendations():
    """Force refresh recommendations for the current user"""
    try:
        update_user_recommendations(current_user.id, limit=10)
        flash("Your recommendations have been refreshed!", "success")
    except Exception as e:
        flash("Could not refresh recommendations. Please try again later.", "warning")
        print(f"Error refreshing recommendations: {e}")
    
    return redirect(url_for('dashboard'))


# Load more posts route, this is used for the songwall activity 
@app.route('/load_more_posts', methods=['GET'])
@login_required
def load_more_posts():
    offset = int(request.args.get('offset', 0))
    posts = get_recent_posts(10, offset)

    posts_data = [
        {
            "username": post.user.username,
            "profile_url": url_for('view_profile', username=post.user.username),  # URL to the profile page
            "song_name": post.song.track_name,
            "artist_name": post.song.artist_name,
            "song_id": post.song.id,  # Song ID for the song page
            "post_message": post.post_message,
            "timestamp": post.time_stamp.strftime("%Y-%m-%d %H:%M:%S"),
            "theme_color": post.user.theme_color or 'var(--primary)'  # Add theme color

        }
        for post in posts
    ]
    
    return jsonify(posts_data)


#Search page
@app.route('/search', methods=['GET', 'POST'])
@login_required
def search():
    songs = []
    if request.method == 'POST':
        query = request.form['search_query']  # Get the search query from the form
        songs = search_songs(query, g.access_token)  # Search for the song in the database or via Spotify

        if not songs:
            flash("No songs found.", "danger")
        else:
            add_songs_to_db(songs)

    return render_template('search.html', songs=songs)

#Search friends route
@app.route('/search_friends', methods=['POST'])
@login_required
def search_friends():
    username = request.form.get('username')
    user = User.query.filter_by(username=username).first()

    if user:
        return redirect(url_for('view_profile', username=user.username))
    else:
        flash('User not found.', 'danger')
        return redirect(url_for('search'))

#Rate page
@app.route('/rate/<string:spotify_id>', methods=['GET', 'POST'])
@login_required
def rate(spotify_id):
    song = get_song_spotify_id_meth(spotify_id)  # User selects song from the search page and we are able to query our database for said song from spotify id now

    if not song:
        flash("Song not found", "error")

    if request.method == 'POST':
        rating = request.form['rating']  # Get the rating from the form
        comment = request.form.get('comment', '')  #Get the comment from the form if its there

        result = add_or_update_rating(current_user.id, current_user.username, spotify_id, rating, comment)  # Call my add/update function to update or db 
        if "error" in result:
            flash(result["error"], "error")

        return redirect(url_for('dashboard'))  

    return render_template('rate.html', song=song)

#View page for songs by our db id
@app.route('/view/<int:song_id>', methods=['GET'])
def view_song(song_id):
    song_info, average_rating = get_song_by_id(song_id)
    ratings = get_song_recent_ratings(song_id)
    posts = get_songs_recent_posts(song_id)

    session = db.session()
    try:
        if song_info:
            # Refresh the song_info object to make sure it is attached to the session
            session.refresh(song_info)
    except Exception as e:
        print(f"Error refreshing song info: {e}")
    finally:
        session.close()

    user_id = current_user.id if current_user.is_authenticated else None
    record_song_view(user_id, song_id)

    if not song_info:
        return "Song not found", 404  # Handle case where song doesn't exist

    return render_template('song.html', song_info=song_info, ratings=ratings, posts=posts, average_rating=average_rating)

#View page for songs by spotify id
@app.route('/search/view/<string:spotify_id>', methods=['GET'])
def search_view_song(spotify_id):
    song_info, average_rating= get_song_by_spotify_id(spotify_id)
    ratings = get_search_song_recent_ratings(spotify_id)
    posts = get_search_song_recent_posts(spotify_id)
    
    session = db.session()
    try:
        if song_info:
            # Refresh the song_info object to make sure it is attached to the session
            session.refresh(song_info)
    except Exception as e:
        print(f"Error refreshing song info: {e}")
    finally:
        session.close()

    user_id = current_user.id if current_user.is_authenticated else None
    record_song_view(user_id, song_info.id)

    if not song_info:
        return "Song not found", 404  # Handle case where song doesn't exist

    return render_template('song.html', song_info=song_info, ratings=ratings, average_rating=average_rating, posts=posts)


@app.route('/search/suggestions', methods=['GET'])
def search_suggestions():
    query = request.args.get('query', '')
    if query:
        # Query the database for song suggestions (e.g., matching track names)
        songs = Song.query.filter(Song.track_name.ilike(query + '%')).order_by(Song.views.desc()).limit(10).all()
        suggestions = [{
            'name': song.track_name,
            'artist': song.artist_name,
            'album_name': song.album_name,
            'album_image_url': song.album_image,
            'spotify_url': song.spotify_url,
            'spotify_id': song.spotify_id
        } for song in songs]
        return jsonify(suggestions)
    return jsonify([])  # Return empty list if no query


#User profile page, allows user to edit and view their profile 
@app.route('/profile', methods=['GET'])
def profile():
    # Check if this is a share link (public access) or authenticated access

    if not current_user.is_authenticated:
        return redirect(url_for('login'))  # Or your login route
    user = current_user

    user_ratings, ratings_ct, avg_ratings = get_user_ratings(user.id)
    pinned_rating = Rating.query.filter_by(user_id=user.id, is_pinned=True).first()
    return render_template(
        'profile.html',
        ratings=user_ratings,
        ratings_ct=ratings_ct,
        avg_ratings=avg_ratings,
        pinned_rating=pinned_rating,
        current_user=user  # Pass user explicitly since it might not be current_user
    )


@app.route('/pin_rating/<int:rating_id>', methods=['POST'])
@login_required
def pin_rating(rating_id):
    # Handle form submission with rating_id from POST data
    rating_id = request.form.get('rating_id')
    success, message = pin_or_unpin_rating(current_user, rating_id)
    
    flash(message, 'success' if success else 'error')
    return redirect(url_for('profile'))



@app.route('/unpin_song', methods=['POST'])
@login_required
def unpin_song():
    pinned_rating = Rating.query.filter_by(user_id=current_user.id, is_pinned=True).first()
    if pinned_rating:
        pinned_rating.is_pinned = False
        db.session.commit()
        flash('Song unpinned successfully!', 'success')
    return redirect(url_for('profile'))


#Route for following users
@app.route('/follow/<int:followed_id>', methods=['POST'])
@login_required
def follow_route(followed_id):
    result = follow_user(followed_id)
    flash(result["message"], "success" if result["success"] else "danger")
    return redirect(url_for('dashboard'))

#Route for unfollowing users
@app.route('/unfollow/<int:followed_id>', methods=['POST'])
@login_required
def unfollow_route(followed_id):
    result = unfollow_user(followed_id)
    flash(result["message"], "success" if result["success"] else "danger")
    return redirect(url_for('dashboard'))


#Logged in user settings page
@app.route('/settings', methods=['GET', 'POST'])
@login_required
def profile_settings():
    user_id = current_user.id
    user = User.query.get(user_id)
    ratings = Rating.query.filter_by(user_id=user_id).join(Song).all()
    posts = Post.query.filter_by(user_id=user_id).join(User).all()

    if request.method == 'POST':
        form_type = request.form.get("form_type")  # Identify which form was submitted

        if form_type == "bio":
            new_bio = request.form.get("biography")
            if len(new_bio)>255:
                flash("Bio length exceeds maximum length, try again", 'error')
            else:
                user.bio = new_bio
                db.session.commit()
                flash("Biography updated successfully!", "success")

        elif form_type == "theme":
            new_color = request.form.get("theme_color")
            if new_color:
                user.theme_color = new_color
                db.session.commit()
                flash("Theme updated successfully!", "success")

        elif form_type == "remove_song":
            song_id = request.form.get("song_id")
            rating_to_delete = Rating.query.filter_by(user_id=user_id, song_id=song_id).first()
            if rating_to_delete:
                db.session.delete(rating_to_delete)
                db.session.commit()
                flash("Rating successfully deleted!", "success")

        elif form_type == "remove_post":
            post_id = request.form.get("post_id")
            post_to_delete = Post.query.filter_by(user_id=user_id, id =post_id).first()
            if post_to_delete:
                db.session.delete(post_to_delete)
                db.session.commit()
                flash("Post deleted", "success")

        return redirect(url_for('profile_settings'))  # Prevent form resubmission on refresh

    return render_template('settings.html', ratings=ratings, posts=posts)

#Update color theme route
@app.route('/update_theme', methods=['POST'])
@login_required
def update_theme():
    color = request.form.get("theme_color")
    if color:
        current_user.theme_color = color
        db.session.commit()
        flash("Theme updated successfully!", "success")
    return redirect(url_for("profile_settings"))


#View user profile by user name
@app.route('/view/<string:username>', methods=['GET'])
def view_profile(username):
    profile_info = get_profile_info(username)
    if not profile_info:
        return redirect(url_for('dashboard'))

    # If the user is logged in, check for additional logic.
    if current_user.is_authenticated:
        if current_user.username == username:
            return redirect(url_for('profile'))
        is_following = check_if_following(current_user.id, profile_info["user"].id)
    else:
        # If not logged in, set is_following to a default value (or handle it as needed).
        is_following = False

    return render_template('view_profile.html', profile_info=profile_info, is_following=is_following)


#View user posts page, for anyone by username will show posts from this user
@app.route('/user_posts/<string:username>', methods=['GET'])
@login_required
def view_posts(username):
    posts_info, userinfo = get_recent_user_posts(username)
    return render_template('user_posts.html', posts_info=posts_info, userinfo=userinfo)

#Table view page
@app.route('/admin/<string:password>/tables', methods=['GET', 'POST'])
def tables(password):
    if password != os.environ.get('SIM_KEY'):
        return redirect(url_for('index'))
    songs = get_all_song_info()
    posts = get_all_posts_info()
    ratings = get_all_ratings_info()
    users = get_all_user_info()

    return render_template('tables.html', songs=songs, users=users, posts=posts, ratings=ratings)


#Admin panel page, will only  work for people with password, and allows for simulation, viewing of all database data, data anaylsis, and moderation of accounts
@app.route('/admin/<string:password>', methods=['POST', 'GET'])
def simulate(password):
    if password != os.environ.get('SIM_KEY'):
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        form_type = request.form.get("form_type")  # Identify which form was submitted

        if form_type == "user_sim":
            amount = request.form.get("user_sim")
            try:
                amount = int(amount)
                if amount:
                    create_users(amount)
                    flash("Users simulated successfully!", "success")
                    return render_template('admin.html')
            except:
                flash("Invalid number of users!", "error")
        elif form_type =="search_sim":
            search_sim()
            flash("40 random song queries performed, song database should be more populated", "success")
            return render_template('admin.html')
        elif form_type == "rate_sim":
            rate_sim()
            flash("Users have rated randomly selected songs","success")
            return render_template('admin.html')
        elif form_type == "delete_example_users":
            success, message = delete_example_users()
            flash(message, "success" if success else "error")
            return render_template('admin.html', password=password)
        elif form_type == "delete_user":
            user_id_to_delete = request.form.get("user_id_to_delete")
            try:
                user_id_to_delete = int(user_id_to_delete)
                success, message = delete_user_by_id(user_id_to_delete)
                flash(message, "success" if success else "error")
            except ValueError:
                flash("Invalid user ID!", "error")
            return render_template('admin.html', password=password)

    return render_template('admin.html', password=password)

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5000)


#if __name__ == "__main__":
 #   app.run(debug=True, host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))