import bcrypt
from sqlalchemy import Boolean, Column, Integer, String, ForeignKey, func
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from flask import Flask
from flask_login import UserMixin



app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///songwall.db'  # You can change the URI to match your preferred database
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class User(db.Model, UserMixin):
    __tablename__ = 'users'
    id = db.Column(Integer, primary_key=True)
    first_name = db.Column(String(100), nullable=False)
    username = db.Column(String(100), unique=True, nullable=False)
    email = db.Column(String(100), unique=True, nullable=False)
    password_hash = db.Column(String(50), nullable=False)
    linked_accounts = db.Column(String(255), nullable=True)  #will need alot more for this, probably more tables based on the social its from
    private_messages = db.Column(Boolean, default=True)
    theme_color = db.Column(String(7), default="#333")
    bio = db.Column(String(255), nullable=True)

    def __repr__(self):
        return f"<User(username='{self.username}')>"
    
    def is_active(self):
        return True  
    
    def get_id(self):
        return str(self.id)  
    
    def set_theme_color(self, color):
        self.theme_color = color
    
    def set_firstname(self, first_name):
        self.first_name = first_name
    
    def set_username(self, username):
        self.username = username
    
    def set_password(self, password):
        """Hash the password and set it."""
        self.password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    def check_password(self, password):
        """Check if the provided password matches the stored hash."""
        return bcrypt.checkpw(password.encode('utf-8'), self.password_hash.encode('utf-8'))
    

class Song(db.Model):
    __tablename__ = 'songs'
    id = db.Column(Integer, primary_key=True)
    track_name = db.Column(String(255), nullable=False)
    artist_name = db.Column(String(255), nullable=False)
    spotify_url = db.Column(db.String(255), nullable=False)
    album_name = db.Column(db.String(200), nullable=True)
    album_image = db.Column(db.String(255), nullable=True)
    release_date = db.Column(db.String(255), nullable=True)
    spotify_id = db.Column(db.String(120), unique=True, nullable=True)  

    ratings = relationship('Rating', backref='song', lazy=True)

    def __repr__(self):
        return f"<Song(track_name='{self.track_name}', artist_name='{self.artist_name}')>"


class Rating(db.Model):
    __tablename__ = 'ratings'
    id = db.Column(Integer, primary_key=True)
    rating = db.Column(Integer, nullable=False)
    comment = db.Column(String(600), nullable=True)
    time_stamp = db.Column(db.DateTime, default=func.now(), nullable=False)
    song_id = db.Column(Integer, ForeignKey('songs.id'), nullable=False)
    user_id = db.Column(Integer, ForeignKey('users.id'), nullable=False)
    username = db.Column(String, ForeignKey('users.username'), nullable=False)

    def __repr__(self):
        return f"<Rating(user_id='{self.user_id}', song_id='{self.song_id}', rating='{self.rating}')>"
    

class Post(db.Model):
    __tablename__ = 'posts'
    id = db.Column(Integer, primary_key=True)
    post_message = db.Column(String(255), nullable=False)
    time_stamp = db.Column(db.DateTime, default=func.now(), nullable=False)
    reference = db.Column(db.String(255), nullable=False)  
    user_id = db.Column(Integer, ForeignKey('users.id'), nullable=False)
    song_id = db.Column(Integer, ForeignKey('songs.id'), nullable=False)

    user = relationship('User', backref='posts')
    song = relationship('Song', backref='posts')

    def __repr__(self):
        return f"<Post(user_id='{self.user_id}', post_message='{self.post_message}')>"




if __name__ == "__main__":
    with app.app_context():
        db.create_all()  # Creates all the tables
    print("Database created successfully!")