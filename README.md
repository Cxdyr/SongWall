# 🎵 Songwall

**Songwall** is a full-stack web application built with **Flask** and deployed on **Heroku**, designed for discovering, rating, and recommending music. It integrates with the **Spotify Web API** to fetch real-time song metadata and uses a **PostgreSQL** database to persist user data, song information, and engagement metrics.

🔗 Live Site: [https://songwall.org](https://songwall.org)

## ⚙️ Features

- **Flask-based Backend**: Modular Flask application with Blueprints for scalable and maintainable code structure.
- **User Authentication System**: Secure login and registration using Flask sessions.
- **Spotify Web API Integration**: Dynamically fetches metadata (artist, album, popularity, audio features, etc.) for songs.
- **PostgreSQL Database**: Hosted on Heroku; stores user accounts, song metadata, ratings, comments, views, and social interactions.
- **Dynamic Song Discovery**:
  - Browse trending songs based on global user activity.
  - View the most viewed and top-rated songs.
- **Recommendation Engine**:
  - Custom algorithm combining:
    - Spotify song metadata (e.g., danceability, energy, tempo)
    - User ratings and interactions
    - Platform-wide social trends
  - Generates tailored music suggestions as users browse.
- **Search Functionality**: Search for songs by title, artist, or genre using Spotify's API.
- **User Profiles**:
  - Display user's rated songs, comments, profile details, and pinned favorite song.
  - Public-facing profile pages to showcase musical tastes.

## 🧰 Tech Stack

- **Backend**: Python, Flask, Flask Blueprints, Jinja2
- **Database**: PostgreSQL (SQLAlchemy ORM), hosted on Heroku
- **API Integration**: Spotify Web API
- **Frontend**: HTML, CSS, JavaScript (vanilla), Jinja templates
- **Hosting**: Heroku (with automatic deployment pipeline)

---

Feel free to explore the app at [**songwall.org**](https://songwall.org) and discover your next favorite track.
