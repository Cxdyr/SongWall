from flask import Flask, app, render_template, request, jsonify, redirect, url_for, flash
from flask_login import LoginManager, login_user, login_required, logout_user
from config import Config
from models import User, db
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

#pop_songs = get_popular_songs()   # In implementation this will need to be in a nested function that calls all once daily population operations once a day on a 24hr time loop, for dev we have it here


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        # Check if email already exists
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('Email address already in use', 'danger')
            return redirect(url_for('register'))

        # Create new user and set hashed password
        new_user = User(email=email)
        new_user.set_password(password)  # Hash  password

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
            flash('Login failed. Check your email and/or password.', 'danger')
    
    return render_template('login.html')


@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')



if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5000)