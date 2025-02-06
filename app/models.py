import bcrypt
from sqlalchemy import Boolean, Column, Integer, String, ForeignKey, func
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from flask_login import UserMixin

# Create the SQLAlchemy instance without a Flask app.
db = SQLAlchemy()

class User(db.Model, UserMixin):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    first_name = Column(String(100), nullable=False)
    username = Column(String(100), unique=True, nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    password_hash = Column(String(100), nullable=False)
    linked_accounts = Column(String(255), nullable=True)
    private_messages = Column(Boolean, default=True)
    theme_color = Column(String(7), default="#333")
    bio = Column(String(255), default="", nullable=True)

    posts = db.relationship('Post', back_populates='user', cascade='all, delete-orphan')
    ratings = db.relationship('Rating', back_populates='user', cascade='all, delete-orphan')
    recommendations = db.relationship('Recommendation', back_populates='user', cascade='all, delete-orphan')
    following = db.relationship('Follow', foreign_keys='Follow.follower_id', cascade='all, delete-orphan')
    followers = db.relationship('Follow', foreign_keys='Follow.followed_id', cascade='all, delete-orphan')

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
    

class Follow(db.Model):
    __tablename__ = 'follows'
    id = Column(Integer, primary_key=True)
    follower_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    followed_id = Column(Integer, ForeignKey('users.id'), nullable=False)

    follower = db.relationship('User', foreign_keys=[follower_id], back_populates='following')
    followed = db.relationship('User', foreign_keys=[followed_id], back_populates='followers')

    def __repr__(self):
        return f"<Follow(follower='{self.follower.username}', followed='{self.followed.username}')>"

class Song(db.Model):
    __tablename__ = 'songs'
    id = Column(Integer, primary_key=True)
    track_name = Column(String(255), nullable=False)
    artist_name = Column(String(255), nullable=False)
    spotify_url = Column(String(255), nullable=False)
    album_name = Column(String(200), nullable=True)
    album_image = Column(String(255), nullable=True)
    release_date = Column(String(255), nullable=True)
    spotify_id = Column(String(120), unique=True, nullable=True)  

    ratings = db.relationship('Rating', back_populates='song', cascade='all, delete-orphan')
    posts = db.relationship('Post', back_populates='song', cascade='all, delete-orphan')
    recommendations = db.relationship('Recommendation', back_populates='song', cascade='all, delete-orphan')

    def __repr__(self):
        return f"<Song(track_name='{self.track_name}', artist_name='{self.artist_name}')>"

class Rating(db.Model):
    __tablename__ = 'ratings'
    id = Column(Integer, primary_key=True)
    rating = Column(Integer, nullable=False)
    comment = Column(String(600), nullable=True)
    time_stamp = Column(db.DateTime, default=func.now(), nullable=False)
    song_id = Column(Integer, ForeignKey('songs.id'), nullable=False)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    username = Column(String, nullable=False)

    user = db.relationship('User', foreign_keys=[user_id], back_populates='ratings')
    song = db.relationship('Song', back_populates='ratings')

    def __repr__(self):
        return f"<Rating(user_id='{self.user_id}', song_id='{self.song_id}', rating='{self.rating}')>"
    

class Post(db.Model):
    __tablename__ = 'posts'
    id = Column(Integer, primary_key=True)
    post_message = Column(String(255), nullable=False)
    time_stamp = Column(db.DateTime, default=func.now(), nullable=False)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    song_id = Column(Integer, ForeignKey('songs.id'), nullable=False)

    user = db.relationship('User', back_populates='posts')
    song = db.relationship('Song', back_populates='posts')

    def __repr__(self):
        return f"<Post(user_id='{self.user_id}', post_message='{self.post_message}')>"

class Recommendation(db.Model):
    __tablename__ = 'recommendations'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    song_id = Column(Integer, ForeignKey('songs.id'), nullable=False)
    recommendation_score = Column(db.Float, nullable=False)

    user = db.relationship('User', back_populates='recommendations')
    song = db.relationship('Song', back_populates='recommendations')
