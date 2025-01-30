from flask import Flask, app, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from api_auth import get_access_token
from config import Config
from models import Song, User, db
from songwall_search import search_songs
from db_functions import add_or_update_rating, get_popular_songwall_songs, get_profile_info, get_song_by_spotify_id, get_top_rated_songs, get_user_ratings, get_recent_ratings
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime


app = Flask(__name__)

scheduler = BackgroundScheduler()  # this is scheduler used to refresh the popular songs and top rated songs on 24 hour loop

pop_songs_cache = None
top_rated_songs_cache = None

# Function to update the cache every 24 hours
def update_cached_data():
    global pop_songs_cache, top_rated_songs_cache
    pop_songs_cache = get_popular_songwall_songs(10)
    top_rated_songs_cache = get_top_rated_songs(10)
    print(f"Cache updated at {datetime.now()}")

    
app.config.from_object(Config)
db.init_app(app)

login_manager = LoginManager(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

access_token = get_access_token()


@app.route('/')
def index():
    if pop_songs_cache is None or top_rated_songs_cache is None:
        update_cached_data()
    return render_template('index.html', pop_songs=pop_songs_cache, top_rated_songs=top_rated_songs_cache)


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        username = request.form['username']
        password = request.form['password']
        first_name = request.form['first_name']

        # Check if email already exists
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('Email address already in use', 'error')
            return redirect(url_for('register'))
        
        existing_username = User.query.filter_by(username=username).first()
        if existing_username:
            flash('Username already in use, please try another one', 'error')

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


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        # Fetch user from database
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):  # Check password
            login_user(user)  # Log in the user
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))  # Redirect to logged in view home page
        else:
            flash('Login failed. Check your email and/or password.', 'error')
    
    return render_template('login.html')


@app.route('/logout')
def logout():
    logout_user()
    flash('You have been logged out successfully!', 'info')
    return redirect(url_for('login'))



@app.route('/dashboard', methods=['GET', 'POST'])
@login_required
def dashboard():
    recent_ratings = get_recent_ratings(10)
    return render_template('dashboard.html', recent_ratings=recent_ratings)


@app.route('/search', methods=['GET', 'POST'])
@login_required
def search():
    songs = []
    if request.method == 'POST':
        query = request.form['search_query']  # Get the search query from the form
        songs = search_songs(query, access_token)  # Search for the song in the database or via Spotify

        if not songs:
            flash("No songs found.", "danger")
        else:
            for song_data in songs:
                # Check if the song already exists in the database using spotify_id
                existing_song = Song.query.filter_by(spotify_id=song_data['spotify_id']).first()
            
                if not existing_song:
                    # If song doesn't exist, create a new song entry for our DB
                    new_song = Song(
                        track_name=song_data['name'],  
                        artist_name=song_data['artist'],  
                        album_image=song_data['album_image_url'],  
                        spotify_url=song_data['spotify_url'],
                        spotify_id=song_data['spotify_id'],  
                        album_name = song_data['album_name']
                    )
                    db.session.add(new_song)
                    db.session.commit()

    return render_template('search.html', songs=songs)



@app.route('/rate/<string:spotify_id>', methods=['GET', 'POST'])
@login_required
def rate(spotify_id):
    song = get_song_by_spotify_id(spotify_id)  #User selects song from the search page and we are able to query our database for said song from spotify id now

    if not song:
        flash("Song not found.", "error")
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        rating = request.form['rating']  # Get the rating from the form
        comment = request.form.get('comment', '')  #Get the comment from the form if its there

        result = add_or_update_rating(current_user.id, current_user.username, spotify_id, rating, comment)  # Call my add/update function to update or db 
        if "error" in result:
            flash(result["error"], "error")
        else:
            flash(result["success"], "success")

        return redirect(url_for('dashboard'))  

    return render_template('rate.html', song=song)



@app.route('/profile', methods=['GET'])
@login_required
def profile():
    user_id = current_user.id
    user_ratings = get_user_ratings(user_id)  # Calling my function to get rated songs from user db 
    return render_template('profile.html', ratings=user_ratings)


@app.route('/view/<string:username>', methods=['GET'])
@login_required
def view_profile(username):
    profile_info = get_profile_info(username)
    
    if profile_info:
        return render_template('view_profile.html', profile_info=profile_info)
    else:
        return redirect(url_for('dashboard'))

    

# this starts the scheduler to update each day
scheduler.add_job(func=update_cached_data, trigger='interval', hours=24)
scheduler.start()

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5000)