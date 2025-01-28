import bcrypt
from sqlalchemy import Boolean, Column, Integer, String, ForeignKey
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from flask import Flask


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///songwall.db'  # You can change the URI to match your preferred database
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class User(db.Model):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    first_name = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    password_hash = Column(String(50), nullable=False)
    linked_accounts = Column(String(255), nullable=True)  #will need alot more for this, probably more tables based on the social its from
    private_messages = Column(Boolean, default=True)

    def __repr__(self):
        return f"<User(username='{self.username}')>"
    
    def is_active(self):
        return True  
    
    def get_id(self):
        return str(self.id)  
    
    def set_firstname(self, first_name):
        self.first_name = first_name
    
    def set_password(self, password):
        """Hash the password and set it."""
        self.password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    def check_password(self, password):
        """Check if the provided password matches the stored hash."""
        return bcrypt.checkpw(password.encode('utf-8'), self.password_hash.encode('utf-8'))
    

class Song(db.Model):
    __tablename__ = 'songs'
    id = Column(Integer, primary_key=True)
    track_name = Column(String(255), nullable=False)
    artist_name = Column(String(255), nullable=False)
    spotify_url = db.Column(db.String(255), nullable=False)
    album_name = db.Column(db.String(200), nullable=True)
    album_image = Column(String(255), nullable=True)
    spotify_id = db.Column(db.String(120), unique=True, nullable=True)  

    ratings = relationship('Rating', backref='song', lazy=True)

    def __repr__(self):
        return f"<Song(track_name='{self.track_name}', artist_name='{self.artist_name}')>"


class Rating(db.Model):
    __tablename__ = 'ratings'
    id = Column(Integer, primary_key=True)
    rating = Column(Integer, nullable=False)
    comment = Column(String(600), nullable=True)
    song_id = Column(Integer, ForeignKey('songs.id'), nullable=False)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)

    def __repr__(self):
        return f"<Rating(user_id='{self.user_id}', song_id='{self.song_id}', rating='{self.rating}')>"


if __name__ == "__main__":
    with app.app_context():
        db.create_all()  # Creates all the tables
    print("Database created successfully!")