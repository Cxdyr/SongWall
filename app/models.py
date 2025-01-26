from sqlalchemy import Boolean, Column, Integer, String, create_engine
from sqlalchemy.orm import declarative_base

Base = declarative_base()    # NOTES , i will be using postgre sql for my actual hosted product, but for now sqlite viewer is nice so im just using what i am familiar with for development (SQLAlchemy and lite)

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    email = Column(String(100), unique=True, nullable=False)
    password_hash = Column(String(50), nullable=False)
    linked_accounts = Column(String(255), nullable=True)  #will need alot more for this, probably more tables based on the social its from
    private_messages = Column(Boolean, default=True)

    def __repr__(self):
        return f"<User(username='{self.username}')>"





engine = create_engine('sqlite:///instance/songwall.db')
Base.metadata.create_all(engine)