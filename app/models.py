import bcrypt
from sqlalchemy import Boolean, Column, Integer, String
from flask_sqlalchemy import SQLAlchemy


db = SQLAlchemy()


class User(db.Model):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
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
    
    def set_password(self, password):
        """Hash the password and set it."""
        self.password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    def check_password(self, password):
        """Check if the provided password matches the stored hash."""
        return bcrypt.checkpw(password.encode('utf-8'), self.password_hash.encode('utf-8'))




