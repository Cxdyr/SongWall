from app.models import db, Song, Rating, User, Recommendation, View, Follow
from sqlalchemy import func, desc
from datetime import datetime, timedelta
from collections import defaultdict
import re
import math

class SongwallRecommender:
    """
    A recommendation system with balanced artist weighting, album preferences, 
    and enhanced diversity, also factoring social factors and general popular songs on songwall - Cody R
    """
    
    def __init__(self):
        # Weights for different recommendation factors
        self.weights = {
            'artist_preference': 0.55,  # Artist preference is weighed the highest
            'album_preference': 0.05,   # Mild album weight
            'popular_songs': 0.20,      # Songs popular with other users
            'view_history': 0.15,       # Based on user's viewing habits
            'social': 0.05              # Based on follows/following
        }
        
        # Rating score weights (more gradual scale)
        self.rating_weights = {
            10: 0.7,     # Highest weight
            9: 0.6,      # Still very high
            8: 0.5,      # Good
            7: 0.3,      # Moderate
            6: 0.15,      # Some interest
            5: -0.1,     # Slight negative
            4: -0.2,     # Negative
            3: -0.4,     # More negative
            2: -0.7,     # Highly negative
            1: -1.0      # Very negative
        }
        
        # Time decay parameters
        self.rating_half_life = 50      # Days until a rating loses half its influence
        self.view_half_life = 14        # Days until a view loses half its influence


        self.recent_ratings_boost = 1.35  # slightly increased boost for recent ratings
        self.recent_ratings_count = 6   # Number of most recent ratings to boost
    
    def _apply_time_decay(self, timestamp, half_life_days):
        """
        Apply exponential time decay to a timestamp, this will be used to ensure recommendations stay fresh
        
        Parameters:
        timestamp (datetime): The timestamp to apply decay to
        half_life_days (int): Number of days for the value to lose half its weight
        
        Returns:
        float: Decay factor between 0 and 1
        """
        if not timestamp:
            return 0.0
            
        # Calculate days since the timestamp
        days_ago = (datetime.now() - timestamp).days
        
        # Prevent negative values (in case of future timestamps)
        days_ago = max(0, days_ago)
        
        # Apply exponential decay formula: 0.5^(days/half_life)
        decay_factor = math.pow(0.5, days_ago / half_life_days)
        
        return decay_factor
    
    def _normalize_title(self, title):
        """
        Normalize a track title to identify different versions of the same song.
        Removes things like "(Live)", "(Remix)", etc.
        """
        if not title:
            return ""
            
        # Convert to lowercase
        title = title.lower()
        
        # Remove common suffixes indicating different versions
        patterns = [
            r'\s*\(feat\..*?\)',
            r'\s*\(ft\..*?\)',
            r'\s*\(featuring.*?\)',
            r'\s*\(with.*?\)',
            r'\s*\(live.*?\)',
            r'\s*\(acoustic.*?\)',
            r'\s*\(remix.*?\)',
            r'\s*\(remaster.*?\)',
            r'\s*\(deluxe.*?\)',
            r'\s*\(bonus.*?\)',
            r'\s*\(radio.*?\)',
            r'\s*\(edit.*?\)',
            r'\s*\(extended.*?\)',
            r'\s*\(version.*?\)',
            r'\s*\(original.*?\)',
            r'\s*\(.*?mix.*?\)',
            r'\s*-\s*.*?remix',
            r'\s*-\s*.*?version',
            r'\s*-\s*remaster.*?'
        ]
        
        for pattern in patterns:
            title = re.sub(pattern, '', title, flags=re.IGNORECASE)
        
        # Remove extra whitespace
        title = ' '.join(title.split())
        
        return title
    
    def _get_balanced_artist_preferences(self, user_id, rated_artist_title_pairs):
        """
        Get artist preferences with balanced weighting to prevent one artist from dominating
        Excludes songs that match artist+title of already rated songs
        Applies time decay to prioritize recent ratings over older stale ones in our db
        We also now apply boost for the recent ratings by 1.35x recent 5 ratings
        """
        # Get all user ratings with song information and timestamps
        all_ratings = db.session.query(Rating.rating, Song.artist_name, Song.id, Rating.time_stamp).join(Song).filter(Rating.user_id == user_id).all()
        
        if not all_ratings:
            return {}
        
        all_ratings.sort(key=lambda x: x[3], reverse=True)

        recent_count = 0 # the amount processed

        
        # Counts ratings per artist and calculate total artist score with time decay
        artist_ratings = defaultdict(list)
        for rating, artist, _, timestamp in all_ratings:
            #checking if its one of the most recent songs, if it is we will boost it, if not we default weight it
            recency_boost = self.recent_ratings_boost if recent_count < self.recent_ratings_count else 1.0
            recent_count += 1
            # Store rating and its timestamp for time decay
            artist_ratings[artist].append((rating, timestamp, recency_boost))
        
        # Get user's rated songs for exclusion
        rated_songs = db.session.query(Rating.song_id).filter(Rating.user_id == user_id).all()
        rated_song_ids = [r[0] for r in rated_songs]
        
        # Calculate artist scores with diminishing returns for multiple ratings and time decay
        artist_scores = {}
        for artist, ratings_with_time in artist_ratings.items():
            # Calculate base score from ratings with time decay
            rating_score = 0
            for rating, timestamp, recency_boost in ratings_with_time:
                # Apply time decay factor based on rating timestamp
                time_factor = self._apply_time_decay(timestamp, self.rating_half_life)
                # Add weighted rating
                rating_score += self.rating_weights.get(rating, 0) * time_factor * recency_boost
            
            # Apply diminishing returns for multiple ratings of the same artist
            if len(ratings_with_time) > 2:
                # Apply diminishing returns formula
                rating_score = rating_score / (1 + 0.3 * (len(ratings_with_time) - 1))
            
            artist_scores[artist] = rating_score
        
        # Normalize artist scores
        total = sum(abs(score) for score in artist_scores.values())
        if total > 0:
            for artist in artist_scores:
             artist_scores[artist] /= total
        
        # Get unrated songs by each artist, excluding different versions of already rated songs
        song_scores = {}
        
        # Get all candidate songs
        candidate_songs = db.session.query(Song.id, Song.artist_name, Song.track_name).filter(Song.id.notin_(rated_song_ids)).all()
        
        # Filter by artist and check for duplicate versions
        for song_id, artist, title in candidate_songs:
            if artist in artist_scores:
                # Check if this is a different version of an already rated song
                if (artist, self._normalize_title(title)) not in rated_artist_title_pairs:
                    song_scores[song_id] = artist_scores[artist]
        
        return song_scores
    
    def _get_album_preferences(self, user_id, rated_artist_title_pairs):
        """
        Get album preferences based on user ratings with time decay
        Adds a mild weight to songs from albums the user has rated highly
        Excludes different versions of already rated songs
        """
        # Get all user ratings with album information and timestamps
        album_ratings = db.session.query(Rating.rating, Song.album_name, Song.id, Rating.time_stamp).join(Song).filter(Rating.user_id == user_id, Song.album_name.isnot(None)).all()
        
        if not album_ratings:
            return {}
        
        # Group ratings by album with timestamps
        album_rating_groups = defaultdict(list)
        for rating, album, _, timestamp in album_ratings:
            if album:  # Skip None or empty albums
                album_rating_groups[album].append((rating, timestamp))
        
        # Get user's rated songs for exclusion
        rated_songs = db.session.query(Rating.song_id).filter(Rating.user_id == user_id).all()
        rated_song_ids = [r[0] for r in rated_songs]
        
        # Calculate album scores with time decay
        album_scores = {}
        for album, ratings_with_time in album_rating_groups.items():
            # Calculate time-decayed weighted average
            total_weight = 0
            weighted_sum = 0
            
            for rating, timestamp in ratings_with_time:
                # Apply time decay
                time_factor = self._apply_time_decay(timestamp, self.rating_half_life)
                weighted_sum += rating * time_factor
                total_weight += time_factor
            
            # Calculate weighted average
            if total_weight > 0:
                avg_rating = weighted_sum / total_weight
                # Convert to 0-1 scale
                normalized_score = (avg_rating - 1) / 9  # 1-10 scale to 0-1
                album_scores[album] = normalized_score
        
        # Find songs from these albums, excluding different versions of rated songs
        song_scores = {}
        
        # Get all candidate songs
        candidate_songs = db.session.query(Song.id, Song.artist_name, Song.track_name, Song.album_name).filter(Song.id.notin_(rated_song_ids), Song.album_name.isnot(None)).all()
        
        # Filter by album and check for duplicate versions
        for song_id, artist, title, album in candidate_songs:
            if album in album_scores:
                # Check if this is a different version of an already rated song
                if (artist, self._normalize_title(title)) not in rated_artist_title_pairs:
                    song_scores[song_id] = album_scores[album]
        
        return song_scores
    
    def _get_popular_songs(self, exclude_song_ids, rated_artist_title_pairs):
        """
        Get popular songs based on views that the user hasn't rated
        Excludes different versions of already rated songs
        Prioritizes recent views
        """
        # Get popular songs in the last 30 days
        month_ago = datetime.now() - timedelta(days=30)
        
        # Get view counts for songs with timestamps
        popular_view_counts = db.session.query(Song.id, func.count(View.id).label('view_count')).join(View).filter(View.timestamp >= month_ago, Song.id.notin_(exclude_song_ids)).group_by(Song.id).all()
        
        # Create a dictionary of song_id -> view_count
        view_count_dict = {song_id: count for song_id, count in popular_view_counts}
        
        # If we don't have enough recent views, include all-time views but with less weight
        if len(popular_view_counts) < 50:
            all_time_views = db.session.query(Song.id, func.count(View.id).label('view_count')).join(View).filter(Song.id.notin_(exclude_song_ids)).group_by(Song.id).all()
            
            # Update the view count dictionary with all-time views for songs not already included
            for song_id, count in all_time_views:
                if song_id not in view_count_dict:
                    view_count_dict[song_id] = count * 0.5  # Heavily discount older views
        
        # Get song details for filtering duplicate versions
        song_details = db.session.query(Song.id, Song.artist_name, Song.track_name).filter(Song.id.in_(list(view_count_dict.keys()))).all()
        
        # Filter out different versions of already rated songs
        filtered_song_ids = []
        for song_id, artist, title in song_details:
            if (artist, self._normalize_title(title)) not in rated_artist_title_pairs:
                filtered_song_ids.append(song_id)
        
        # Calculate normalized scores for filtered songs
        song_scores = {}
        if filtered_song_ids:
            max_views = max(view_count_dict[song_id] for song_id in filtered_song_ids)
            
            for song_id in filtered_song_ids:
                # Score is normalized by max view count
                song_scores[song_id] = view_count_dict[song_id] / max_views
        
        return song_scores
    
    def _get_view_based_recommendations(self, user_id, exclude_song_ids, rated_artist_title_pairs):
        """
        Get recommendations based on user's viewing history with time decay
        Excludes different versions of already rated songs
        """
        # Get artists from user's viewing history with timestamps
        viewed_artists_with_time = db.session.query(Song.artist_name, View.timestamp).join(View).filter(View.user_id == user_id).order_by(View.timestamp.desc()).all()
        
        if not viewed_artists_with_time:
            return {}
            
        # Calculate artist view scores with time decay
        artist_views = defaultdict(list)
        for artist, timestamp in viewed_artists_with_time:
            artist_views[artist].append(timestamp)
        
        # Calculate time-decayed scores for each artist
        artist_scores = {}
        total_score = 0
        
        for artist, timestamps in artist_views.items():
            # Apply time decay to each view and sum
            artist_score = 0
            for timestamp in timestamps:
                time_factor = self._apply_time_decay(timestamp, self.view_half_life)
                artist_score += time_factor
            
            # Apply diminishing returns for many views of the same artist
            if len(timestamps) > 5:
                artist_score = artist_score / (1 + 0.2 * (len(timestamps) - 5))
                
            artist_scores[artist] = artist_score
            total_score += artist_score
        
        # Normalize artist scores
        if total_score > 0:
            for artist in artist_scores:
                artist_scores[artist] /= total_score
        
        # Get songs by these artists, excluding different versions of rated songs
        song_scores = {}
        
        # Get all candidate songs
        candidate_songs = db.session.query(Song.id, Song.artist_name, Song.track_name).filter(Song.id.notin_(exclude_song_ids), Song.artist_name.in_(list(artist_scores.keys()))).all()
        
        # Filter and score songs
        for song_id, artist, title in candidate_songs:
            # Check if this is a different version of an already rated song
            if (artist, self._normalize_title(title)) not in rated_artist_title_pairs:
                song_scores[song_id] = artist_scores[artist]
        
        return song_scores
    
    def _get_social_recommendations(self, user_id, exclude_song_ids, rated_artist_title_pairs):
        """
        Get recommendations based on social connections with time decay for ratings
        Excludes different versions of already rated songs
        """
        # Find users this user follows
        follows = db.session.query(Follow.followed_id).filter(Follow.follower_id == user_id).all()
        followed_ids = [f[0] for f in follows]
        
        if not followed_ids:
            return {}
            
        # Get rated songs from followed users with timestamps
        followed_ratings_with_time = db.session.query(Rating.song_id, Rating.rating, Rating.time_stamp, Rating.user_id).filter(Rating.user_id.in_(followed_ids), Rating.song_id.notin_(exclude_song_ids), Rating.rating >= 6).all()
        
        if not followed_ratings_with_time:
            return {}
        
        # Group by song_id to calculate weighted average with time decay
        song_weighted_ratings = defaultdict(list)
        for song_id, rating, timestamp, _ in followed_ratings_with_time:
            song_weighted_ratings[song_id].append((rating, timestamp))
        
        # Calculate time-decayed weighted averages
        song_scores_raw = {}
        
        for song_id, ratings_with_time in song_weighted_ratings.items():
            total_weight = 0
            weighted_sum = 0
            
            for rating, timestamp in ratings_with_time:
                # Apply time decay
                time_factor = self._apply_time_decay(timestamp, self.rating_half_life)
                weighted_sum += rating * time_factor
                total_weight += time_factor
            
            if total_weight > 0:
                # Calculate weighted average
                avg_rating = weighted_sum / total_weight
                # Normalize (6-10 scale to 0-1)
                song_scores_raw[song_id] = (avg_rating - 6) / 4
        
        # Get song details for filtering duplicate versions
        rated_song_ids = list(song_scores_raw.keys())
        
        song_details = db.session.query(
            Song.id, Song.artist_name, Song.track_name
        ).filter(
            Song.id.in_(rated_song_ids)
        ).all()
        
        # Filter out different versions of already rated songs
        song_scores = {}
        for song_id, artist, title in song_details:
            if (artist, self._normalize_title(title)) not in rated_artist_title_pairs:
                song_scores[song_id] = song_scores_raw[song_id]
        
        return song_scores
    
    def _ensure_enhanced_diversity(self, sorted_song_scores, limit):
        """
        Enhanced diversity filter that ensures:
        1. Reasonable variety of artists (allows up to 3 songs from same artist in top positions)
        2. No duplicate track names from same artist
        3. Some variety of albums (allows up to 2 songs from same album)
        """
        artist_count = {}  # Track number of songs per artist
        artist_titles = defaultdict(set)  # Track titles per artist
        album_count = {}  # Track number of songs per album
        diverse_recommendations = []
    
        # Build lookup dictionaries to reduce database queries
        all_song_ids = [song_id for song_id, _ in sorted_song_scores]
        songs = db.session.query(Song.id, Song.artist_name, Song.track_name, Song.album_name).filter(Song.id.in_(all_song_ids)).all()
    
        song_info = {}
        for song_id, artist, title, album in songs:
            song_info[song_id] = {
                'artist': artist,
                'title': title,
                'norm_title': self._normalize_title(title),
                'album': album
            }
    
        # Process songs in order of score
        for song_id, score in sorted_song_scores:
            if song_id not in song_info:
                continue
            
            info = song_info[song_id]
            artist = info['artist']
            title = info['title']
            norm_title = info['norm_title']
            album = info['album']
        
            # Skip if we already have a song with this normalized title from this artist
            if norm_title in artist_titles.get(artist, set()):
                continue
        
            # Apply modified artist diversity rules - allow up to 3 songs from same artist
            # and 2 songs from same album throughout the recommendations
        
            # Check if we've reached the max for this artist or album
            if (artist_count.get(artist, 0) < 3 and  # Allow up to 3 songs per artist
                (not album or album_count.get(album, 0) < 2)):  # Allow up to 2 songs per album
            
                diverse_recommendations.append((song_id, score))
                artist_count[artist] = artist_count.get(artist, 0) + 1
                artist_titles[artist].add(norm_title)
            
                if album:
                    album_count[album] = album_count.get(album, 0) + 1
            
            # Stop when we have enough recommendations
            if len(diverse_recommendations) >= limit:
                break
    
        # If we don't have enough diverse recommendations, add more from the sorted list
        # but still avoid duplicating titles from the same artist
        if len(diverse_recommendations) < limit:
            for song_id, score in sorted_song_scores:
                if song_id not in [s[0] for s in diverse_recommendations] and song_id in song_info:
                    info = song_info[song_id]
                    artist = info['artist']
                    norm_title = info['norm_title']
                
                    # Skip if we already have this normalized title from this artist
                    if norm_title in artist_titles.get(artist, set()):
                        continue
                    
                    diverse_recommendations.append((song_id, score))
                    artist_titles[artist].add(norm_title)
                
                    if len(diverse_recommendations) >= limit:
                        break
        
        return diverse_recommendations
    
    def _filter_duplicate_versions(self, sorted_song_scores, limit):
        """
        Simpler filter that just prevents different versions of the same song
        (same artist+normalized title) without enforcing strict artist diversity
        """
        filtered_recommendations = []
        artist_titles = defaultdict(set)  # Track normalized titles per artist
        
        # Build lookup dictionaries to reduce database queries
        all_song_ids = [song_id for song_id, _ in sorted_song_scores]
        songs = db.session.query(
            Song.id, Song.artist_name, Song.track_name
        ).filter(Song.id.in_(all_song_ids)).all()
        
        song_info = {}
        for song_id, artist, title in songs:
            song_info[song_id] = {
                'artist': artist,
                'norm_title': self._normalize_title(title)
            }
        
        # Process songs in order of score
        for song_id, score in sorted_song_scores:
            if song_id not in song_info:
                continue
                
            info = song_info[song_id]
            artist = info['artist']
            norm_title = info['norm_title']
            
            # Skip if we already have a song with this normalized title from this artist
            if norm_title in artist_titles.get(artist, set()):
                continue
            
            # Add to recommendations
            filtered_recommendations.append((song_id, score))
            artist_titles[artist].add(norm_title)
            
            # Stop when we have enough recommendations
            if len(filtered_recommendations) >= limit:
                break
        
        return filtered_recommendations
    

    
    def generate_for_user(self, user_id, limit=10):
        """
        Generate recommendations for a specific user with diversity controls
        
        Parameters:
        user_id (int): The user to generate recommendations for
        limit (int): Number of recommendations to return
        
        Returns:
        list: List of (song_id, score) tuples
        """
        # Get songs the user has already rated
        rated_songs = db.session.query(Rating.song_id).filter(Rating.user_id == user_id).all()
        rated_song_ids = [r[0] for r in rated_songs]
        
        # Get artist-title pairs the user has already rated to avoid different versions being duplicated
        rated_pairs = db.session.query(Song.artist_name, Song.track_name).filter(Song.id.in_(rated_song_ids)).all()
        
        rated_artist_title_pairs = {(artist, self._normalize_title(title)) for artist, title in rated_pairs}
        
        # Initialize score tracking
        song_scores = defaultdict(float)
        
        # 1.  Get artist preferences with balanced weighting
        artist_scores = self._get_balanced_artist_preferences(user_id, rated_artist_title_pairs)
        
        # 2. Get album preferences
        album_scores = self._get_album_preferences(user_id, rated_artist_title_pairs)
        
        # 3. Get popular songs the user hasn't rated
        popular_scores = self._get_popular_songs(rated_song_ids, rated_artist_title_pairs)
        
        # 4. Get recommendations based on viewing history
        view_scores = self._get_view_based_recommendations(user_id, rated_song_ids, rated_artist_title_pairs)
        
        # 5. Get social recommendations (from follows)
        social_scores = self._get_social_recommendations(user_id, rated_song_ids, rated_artist_title_pairs)
        
        # Combine all scores with weights
        for song_id, score in artist_scores.items():
            song_scores[song_id] += score * self.weights['artist_preference']
            
        for song_id, score in album_scores.items():
            song_scores[song_id] += score * self.weights['album_preference']
            
        for song_id, score in popular_scores.items():
            song_scores[song_id] += score * self.weights['popular_songs']
            
        for song_id, score in view_scores.items():
            song_scores[song_id] += score * self.weights['view_history']
            
        for song_id, score in social_scores.items():
            song_scores[song_id] += score * self.weights['social']

        # Normalize final scores to 0-1 range
        max_score = max(song_scores.values()) if song_scores else 1.0
        if max_score > 0:
            for song_id in song_scores:
                song_scores[song_id] /= max_score
            
        # Sort by score and get top recommendations
        sorted_songs = sorted(song_scores.items(), key=lambda x: x[1], reverse=True)
        
        # Apply diversity filter to ensure variety and no duplicates
        diverse_recommendations = self._ensure_enhanced_diversity(sorted_songs, limit)
        
        # Store recommendations in the database
        self._store_recommendations(user_id, diverse_recommendations, "diverse")
        
        return diverse_recommendations
    
    def generate_pure_recommendations(self, user_id, limit=10):
        """
        Generate recommendations for a specific user without strict diversity controls
        (but still avoiding different versions of the same song)
        
        Parameters:
        user_id (int): The user to generate recommendations for
        limit (int): Number of recommendations to return
        
        Returns:
        list: List of (song_id, score) tuples
        """
        # Get songs the user has already rated
        rated_songs = db.session.query(Rating.song_id).filter(Rating.user_id == user_id).all()
        rated_song_ids = [r[0] for r in rated_songs]
        
        # Get artist-title pairs the user has already rated to avoid different versions
        rated_pairs = db.session.query(
            Song.artist_name, Song.track_name
        ).filter(Song.id.in_(rated_song_ids)).all()
        
        rated_artist_title_pairs = {(artist, self._normalize_title(title)) for artist, title in rated_pairs}
        
        # Initialize score tracking
        song_scores = defaultdict(float)
        
        # Calculate all component scores
        artist_scores = self._get_balanced_artist_preferences(user_id, rated_artist_title_pairs)
        album_scores = self._get_album_preferences(user_id, rated_artist_title_pairs)
        popular_scores = self._get_popular_songs(rated_song_ids, rated_artist_title_pairs)
        view_scores = self._get_view_based_recommendations(user_id, rated_song_ids, rated_artist_title_pairs)
        social_scores = self._get_social_recommendations(user_id, rated_song_ids, rated_artist_title_pairs)
        
        # Combine all scores with weights
        for song_id, score in artist_scores.items():
            song_scores[song_id] += score * self.weights['artist_preference']
            
        for song_id, score in album_scores.items():
            song_scores[song_id] += score * self.weights['album_preference']
            
        for song_id, score in popular_scores.items():
            song_scores[song_id] += score * self.weights['popular_songs']
            
        for song_id, score in view_scores.items():
            song_scores[song_id] += score * self.weights['view_history']
            
        for song_id, score in social_scores.items():
            song_scores[song_id] += score * self.weights['social']
        
        # Sort by score
        sorted_songs = sorted(song_scores.items(), key=lambda x: x[1], reverse=True)
        
        # Simply filter out exact duplicates of artist+title
        filtered_recommendations = self._filter_duplicate_versions(sorted_songs, limit)
        
        # Store recommendations in the database
        self._store_recommendations(user_id, filtered_recommendations, "pure")
        
        return filtered_recommendations
    
    def _store_recommendations(self, user_id, recommendations, rec_type="diverse"):
        """
        Store recommendations in the database with optimized approach for high concurrency
    
        Parameters:
        user_id (int): User ID
        recommendations (list): List of (song_id, score) tuples
        rec_type (str): Type of recommendations ("diverse" or "pure")
        """
        # Get existing recommendations to determine which need updates and which are new
        existing_recs = db.session.query(Recommendation.song_id, Recommendation.id).filter(
            Recommendation.user_id == user_id
        ).all()
    
        # Track existing recommendations and their IDs
        existing_song_map = {song_id: rec_id for song_id, rec_id in existing_recs}
        existing_song_ids = set(existing_song_map.keys())
    
        # Track which songs are in the new recommendations
        new_song_ids = set()
    
        # Process new recommendations
        for song_id, score in recommendations:
            new_song_ids.add(song_id)
        
            if song_id in existing_song_ids:
                # Update existing record using SQLAlchemy's update construct
                db.session.query(Recommendation).filter(
                    Recommendation.id == existing_song_map[song_id]
                ).update(
                    {"recommendation_score": float(score)},
                    synchronize_session=False
                )
            else:
                # Insert new record
                rec = Recommendation(
                    user_id=user_id,
                    song_id=song_id,
                    recommendation_score=float(score)
                )
                db.session.add(rec)
    
        # Delete recommendations that are no longer needed
        to_delete = existing_song_ids - new_song_ids
        if to_delete:
            db.session.query(Recommendation).filter(
                Recommendation.user_id == user_id,
                Recommendation.song_id.in_(to_delete)
            ).delete(synchronize_session=False)
    
        # Commit all changes
        db.session.commit()

# Utility functions
def get_user_recommendations(user_id, limit=10, diverse=True):
    """
    Get recommendations for a user from the database.
    If none exist, generates new ones.
    
    Parameters:
    user_id (int): User ID
    limit (int): Maximum number of recommendations to return
    diverse (bool): Whether to use the diverse recommendation algorithm
    
    Returns:
    list: List of (Song, score) tuples
    """
    # Check if user has recommendations
    recommendations = Recommendation.query.filter_by(user_id=user_id).order_by(Recommendation.recommendation_score.desc()).limit(limit).all()
    
    # If no recommendations, generate new ones
    if not recommendations:
        recommender = SongwallRecommender()
        if diverse:
            recommender.generate_for_user(user_id, limit)
        else:
            recommender.generate_pure_recommendations(user_id, limit)
        
        # Get the newly generated recommendations
        recommendations = Recommendation.query.filter_by(user_id=user_id).order_by(Recommendation.recommendation_score.desc()).limit(limit).all()
    
    # Return recommendations as (Song, score) tuples
    return [(recommendation.song, recommendation.recommendation_score) for recommendation in recommendations]

def update_user_recommendations(user_id, limit=10, diverse=True):
    """
    Force update recommendations for a specific user.
    Used when user refreshes their dashboard.
    
    Parameters:
    user_id (int): User ID
    limit (int): Maximum number of recommendations to return
    diverse (bool): Whether to use the diverse recommendation algorithm
    
    Returns:
    list: List of (Song, score) tuples
    """
    recommender = SongwallRecommender()
    if diverse:
        recommender.generate_for_user(user_id, limit)
    else:
        recommender.generate_pure_recommendations(user_id, limit)
    
    return get_user_recommendations(user_id, limit, diverse)

def generate_all_recommendations(diverse=True):
    """
    Generate recommendations for all users.
    This should be run as a scheduled task (daily/weekly).
    
    Parameters:
    diverse (bool): Whether to use the diverse recommendation algorithm
    """
    recommender = SongwallRecommender()
    users = User.query.all()
    
    for user in users:
        try:
            if diverse:
                recommender.generate_for_user(user.id)
            else:
                recommender.generate_pure_recommendations(user.id)
            print(f"Generated recommendations for user {user.username}")
        except Exception as e:
            print(f"Error generating recommendations for user {user.username}: {e}")
    
    print("Recommendation generation complete")