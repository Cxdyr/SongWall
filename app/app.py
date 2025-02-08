from flask import Flask, app, current_app, jsonify, render_template, request, redirect, url_for, flash, g
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from app.api_auth import get_access_token
from app.models import Post, Rating, Song, User, db
from app.songwall_search import search_songs
from app.db_functions import (
    add_or_update_rating, add_post, add_songs_to_db, check_if_following, create_users, delete_example_users,
    follow_user, get_all_posts_info, get_all_ratings_info, get_all_song_info, get_all_user_info,
    get_popular_songwall_songs, get_potential_songs, get_profile_info, get_rated_songs_by_user, get_recent_follow_ratings,
    get_recent_posts, get_recent_ratings_username, get_recent_user_posts, get_search_song_recent_posts,
    get_search_song_recent_ratings, get_song_by_id, get_song_by_spotify_id, get_song_id_meth,
    get_song_recent_ratings, get_song_spotify_id_meth, get_songs_recent_posts, get_top_rated_songs,
    get_user_ratings, get_recent_ratings, rate_sim, search_sim, unfollow_user
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

    pop_songs, top_rated_songs = get_cached_songs()
    return render_template('index.html', pop_songs=pop_songs, top_rated_songs=top_rated_songs)

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
        # Check if email already exists
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('Email address already in use', 'error')
            return redirect(url_for('register'))
        
        existing_username = User.query.filter(db.func.lower(User.username) == username.lower()).first()
        if existing_username:
            flash('Username already in use, please try another one', 'error')
            return redirect(url_for('register'))

        # Create new user and set hashed password
        new_user = User(email=email)
        new_user.set_password(password)  # Hash  password
        new_user.set_firstname(first_name)
        new_user.set_username(username)

        # Add user to the session and commit
        db.session.add(new_user)
        db.session.commit()

        flash('Account created successfully! Please login.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')

#Login page
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email'].lower()
        password = request.form['password']

        # Fetch user from database
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):  # Check password
            login_user(user)  # Log in the user
            return redirect(url_for('dashboard'))  # Redirect to logged in view home page
        else:
            flash('Login failed. Check your email and/or password.', 'error')
    
    return render_template('login.html')

#Logout route
@app.route('/logout')
def logout():
    logout_user()
    flash('You have been logged out successfully!', 'info')
    return redirect(url_for('login'))


#Logged in home page
@app.route('/dashboard', methods=['GET', 'POST']) 
@login_required
def dashboard():
    followed_ratings = get_recent_follow_ratings(current_user.id)
    recent_ratings = get_recent_ratings(20)  #getting the 10 recent ratings
    potential_songs = get_potential_songs(current_user.id)

    recent_posts = get_recent_posts(10, 0)  # getting the 10 recent posts with offset 0
    user_songs = get_rated_songs_by_user(current_user.id)  # getting the rated songs for the user for posting potential

    if request.method == 'POST':  #if post method it means a user is posting a message so we get the song id for reference FK and the info in the message and post it to db before redirecting back
        song_id = request.form.get('song_id')
        post_message = request.form.get('post_message')

        if song_id and post_message:
            add_post(current_user.id, song_id, post_message) # add post to db 
            return redirect(url_for('dashboard'))
        
    return render_template('dashboard.html', recent_ratings=recent_ratings, followed_ratings=followed_ratings, recent_posts=recent_posts, user_songs=user_songs, potential_songs=potential_songs)




# Load more posts route
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
            "timestamp": post.time_stamp.strftime("%Y-%m-%d %H:%M:%S")
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
        return redirect(url_for('dashboard'))

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

    if not song_info:
        return "Song not found", 404  # Handle case where song doesn't exist

    return render_template('song.html', song_info=song_info, ratings=ratings, posts=posts, average_rating=average_rating)

#View page for songs by spotify id
@app.route('/search/view/<string:spotify_id>', methods=['GET'])
def search_view_song(spotify_id):
    song_info, average_rating= get_song_by_spotify_id(spotify_id)
    ratings = get_search_song_recent_ratings(spotify_id)
    posts = get_search_song_recent_posts(spotify_id)

    if not song_info:
        return "Song not found", 404  # Handle case where song doesn't exist

    return render_template('song.html', song_info=song_info, ratings=ratings, average_rating=average_rating, posts=posts)

#Logged in user profile page, includes settings redirect
@app.route('/profile', methods=['GET'])
@login_required
def profile():
    user_id = current_user.id
    user_ratings, recent_ratings, ratings_ct, avg_ratings = get_user_ratings(user_id)  # Calling my function to get rated songs from user db 
    return render_template('profile.html', ratings=user_ratings,recent_ratings=recent_ratings, ratings_ct=ratings_ct, avg_ratings=avg_ratings)

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
            if new_bio:
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

#View profile page, for anyone by username
@app.route('/view/<string:username>', methods=['GET'])
@login_required
def view_profile(username):
    if current_user.username == username:
        return redirect(url_for('profile'))

    profile_info = get_profile_info(username)
    recent_ratings = get_recent_ratings_username(username)

    is_following = check_if_following(current_user.id, profile_info["user"].id)
    
    if profile_info:
        return render_template('view_profile.html', profile_info=profile_info, recent_ratings=recent_ratings, is_following=is_following)
    else:
        return redirect(url_for('dashboard'))
    
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

    #Loading tons of user data for anaylsis and simulation including db info and more
    return render_template('admin.html', password=password)

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5000)


#if __name__ == "__main__":
#    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))