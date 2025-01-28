from flask import Flask, app, render_template, request, jsonify, redirect, url_for, flash
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from api_auth import get_access_token
from config import Config
from models import Rating, Song, User, db
from songwall_search import search_songs
from songwall_popular_songs import get_popular_songs


app = Flask(__name__)
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
    pop_songs = get_popular_songs(access_token)  # eventually this will be a on a loop that runs periodically - ie every 24 hours or so
    if not pop_songs or not isinstance(pop_songs, list):
        pop_songs = []  #page will load regardless if theres an error
    
    return render_template('index.html', pop_songs=pop_songs)



@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        first_name = request.form['first_name']

        # Check if email already exists
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('Email address already in use', 'danger')
            return redirect(url_for('register'))

        # Create new user and set hashed password
        new_user = User(email=email)
        new_user.set_password(password)  # Hash  password
        new_user.set_firstname(first_name)

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


@app.route('/dashboard')
def dashboard():
    user_name = current_user.first_name
    return render_template('dashboard.html', user_name=user_name)


@app.route('/search', methods=['GET', 'POST'])
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
def rate(spotify_id):
    song = Song.query.filter_by(spotify_id=spotify_id).first()
    
    if request.method == 'POST':
        rating = request.form['rating']  # Get the rating from the form
        comment = request.form.get('comment', '')   # get the comment or a null comment if they choose to keep it blank
        
        user_id = current_user.id

        existing_rating = Rating.query.filter_by(song_id=song.id, user_id=user_id).first()  # checking to make sure haven't already rated this song

        if existing_rating:
            existing_rating.rating = rating    # If it does exist will just override it instead of adding a new one to our records
            existing_rating.comment = comment   
        else:
            new_rating = Rating(rating=rating, comment=comment, song_id=song.id, user_id=user_id)  # if this is a new rating create new record
            db.session.add(new_rating)

        db.session.commit()

        flash("Rating submitted successfully!", "success")
        return redirect(url_for('dashboard'))  # back to dashboard... where user can see their ratings

    return render_template('rate.html', song=song)




if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5000)