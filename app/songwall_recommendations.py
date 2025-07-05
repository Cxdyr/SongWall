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
    
    def __init__(self, user_id):
        self.user_id = user_id
        self.weights = {
            'artist_preference': 0.60,
            'album_preference': 0.05,
            'popular_songs': 0.25,
            'view_history': 0.05,
            'social': 0.05
        }
        self.rating_weights = {
            10: 0.7, 9: 0.6, 8: 0.5, 7: 0.3, 6: 0.15,
            5: -0.1, 4: -0.2, 3: -0.4, 2: -0.7, 1: -1.0
        }
        self.rating_half_life = 30
        self.view_half_life = 7
        self.recent_ratings_boost = 1.25
        self.recent_ratings_count = 5
    
    def _apply_time_decay(self, timestamp, half_life_days):
        """
        Apply exponential time decay to a timestamp
        Optimized with early return and simplified logic
        """
        if not timestamp or not isinstance(timestamp, datetime):
            return 0.0
            
        days_ago = max(0, (datetime.now() - timestamp).days)
        return math.pow(0.5, days_ago / half_life_days)
    
    def _normalize_title(self, title):
        """
        Normalize track title for duplicate detection
        Optimized regex compilation
        """
        if not title:
            return ""
            
        title = title.lower()
        patterns = [
            (r'\s*\(feat\..*?\)', ''),
            (r'\s*\(ft\..*?\)', ''),
            (r'\s*\(featuring.*?\)', ''),
            (r'\s*\(with.*?\)', ''),
            (r'\s*\(live.*?\)', ''),
            (r'\s*\(acoustic.*?\)', ''),
            (r'\s*\(remix.*?\)', ''),
            (r'\s*\(remaster.*?\)', ''),
            (r'\s*\(deluxe.*?\)', ''),
            (r'\s*\(bonus.*?\)', ''),
            (r'\s*\(radio.*?\)', ''),
            (r'\s*\(edit.*?\)', ''),
            (r'\s*\(extended.*?\)', ''),
            (r'\s*\(version.*?\)', ''),
            (r'\s*\(original.*?\)', ''),
            (r'\s*\(.*?mix.*?\)', ''),
            (r'\s*-\s*.*?remix', ''),
            (r'\s*-\s*.*?version', ''),
            (r'\s*-\s*remaster.*?', '')
        ]
        
        for pattern, repl in patterns:
            title = re.sub(pattern, repl, title, flags=re.IGNORECASE)
        
        return ' '.join(title.split())
    
    def _get_balanced_artist_preferences(self, user_id, rated_artist_title_pairs):
        """
        Optimized artist preferences with batch queries and reduced memory usage
        """
        all_ratings = db.session.query(
            Rating.rating, Song.artist_name, Song.id, Rating.time_stamp
        ).join(Song).filter(Rating.user_id == user_id).order_by(Rating.time_stamp.desc()).all()
        
        if not all_ratings:
            return {}
        
        artist_ratings = defaultdict(list)
        recent_count = 0
        
        for rating, artist, song_id, timestamp in all_ratings:
            boost = self.recent_ratings_boost if recent_count < self.recent_ratings_count else 1.0
            artist_ratings[artist].append((rating, timestamp, boost))
            recent_count += 1
        
        rated_song_ids = {r[2] for r in all_ratings}
        
        artist_scores = {}
        for artist, ratings in artist_ratings.items():
            rating_score = sum(
                self.rating_weights.get(rating, 0) * 
                self._apply_time_decay(timestamp, self.rating_half_life) * boost
                for rating, timestamp, boost in ratings
            )
            
            if len(ratings) > 2:
                rating_score /= (1 + 0.3 * (len(ratings) - 1))
            
            artist_scores[artist] = rating_score
        
        total = sum(abs(score) for score in artist_scores.values())
        if total > 0:
            artist_scores = {k: v/total for k, v in artist_scores.items()}
        
        candidate_songs = db.session.query(
            Song.id, Song.artist_name, Song.track_name
        ).filter(Song.id.notin_(rated_song_ids)).all()
        
        song_scores = {
            song_id: artist_scores[artist]
            for song_id, artist, title in candidate_songs
            if artist in artist_scores and (artist, self._normalize_title(title)) not in rated_artist_title_pairs
        }
        
        return song_scores
    
    def _get_album_preferences(self, user_id, rated_artist_title_pairs):
        """
        Optimized album preferences with batch processing
        """
        album_ratings = db.session.query(
            Rating.rating, Song.album_name, Song.id, Rating.time_stamp
        ).join(Song).filter(Rating.user_id == user_id, Song.album_name.isnot(None)).all()
        
        if not album_ratings:
            return {}
        
        album_rating_groups = defaultdict(list)
        for rating, album, _, timestamp in album_ratings:
            if album:
                album_rating_groups[album].append((rating, timestamp))
        
        rated_song_ids = {r[2] for r in album_ratings}
        
        album_scores = {}
        for album, ratings in album_rating_groups.items():
            weighted_sum = sum(
                rating * self._apply_time_decay(timestamp, self.rating_half_life)
                for rating, timestamp in ratings
            )
            total_weight = sum(self._apply_time_decay(timestamp, self.rating_half_life) for _, timestamp in ratings)
            
            if total_weight > 0:
                album_scores[album] = (weighted_sum / total_weight - 1) / 9
        
        candidate_songs = db.session.query(
            Song.id, Song.artist_name, Song.track_name, Song.album_name
        ).filter(Song.id.notin_(rated_song_ids), Song.album_name.isnot(None)).all()
        
        song_scores = {
            song_id: album_scores[album]
            for song_id, artist, title, album in candidate_songs
            if album in album_scores and (artist, self._normalize_title(title)) not in rated_artist_title_pairs
        }
        
        return song_scores
    
    def _get_popular_songs(self, exclude_song_ids, rated_artist_title_pairs):
        """
        Get popular songs based on the 50 most recent views by any registered user, excluding the logged-in user's views.
        Excludes different versions of already rated songs.
        No time decay is applied to prioritize current trends.
        """
        recent_views = db.session.query(
            View.song_id, Song.artist_name, Song.track_name
        ).join(Song).filter(
            View.user_id != self.user_id,
            View.song_id.notin_(exclude_song_ids)
        ).order_by(View.timestamp.desc()).limit(50).all()
    
        song_view_counts = defaultdict(int)
        for song_id, artist, title in recent_views:
            if (artist, self._normalize_title(title)) not in rated_artist_title_pairs:
                song_view_counts[song_id] += 1
    
        song_scores = {}
        if song_view_counts:
            max_views = max(song_view_counts.values())
            song_scores = {
                song_id: count / max_views
                for song_id, count in song_view_counts.items()
            }
    
        return song_scores
    
    def _get_view_based_recommendations(self, user_id, exclude_song_ids, rated_artist_title_pairs):
        """
        Optimized view-based recommendations with time decay
        """
        viewed_artists = db.session.query(
            Song.artist_name, View.timestamp
        ).join(View).filter(View.user_id == user_id).order_by(View.timestamp.desc()).all()
        
        if not viewed_artists:
            return {}
            
        artist_views = defaultdict(list)
        for artist, timestamp in viewed_artists:
            artist_views[artist].append(timestamp)
        
        artist_scores = {}
        total_score = 0
        
        for artist, timestamps in artist_views.items():
            artist_score = sum(self._apply_time_decay(t, self.view_half_life) for t in timestamps)
            
            if len(timestamps) > 5:
                artist_score /= (1 + 0.2 * (len(timestamps) - 5))
                
            artist_scores[artist] = artist_score
            total_score += artist_score
        
        if total_score > 0:
            artist_scores = {k: v/total_score for k, v in artist_scores.items()}
        
        candidate_songs = db.session.query(
            Song.id, Song.artist_name, Song.track_name
        ).filter(Song.id.notin_(exclude_song_ids), Song.artist_name.in_(artist_scores.keys())).all()
        
        song_scores = {
            song_id: artist_scores[artist]
            for song_id, artist, title in candidate_songs
            if (artist, self._normalize_title(title)) not in rated_artist_title_pairs
        }
        
        return song_scores
    
    def _get_social_recommendations(self, user_id, exclude_song_ids, rated_artist_title_pairs):
        """
        Optimized social recommendations with batch processing
        """
        followed_ids = {f[0] for f in db.session.query(Follow.followed_id).filter(Follow.follower_id == user_id).all()}
        
        if not followed_ids:
            return {}
            
        followed_ratings = db.session.query(
            Rating.song_id, Rating.rating, Rating.time_stamp
        ).filter(Rating.user_id.in_(followed_ids), Rating.song_id.notin_(exclude_song_ids), Rating.rating >= 6).all()
        
        if not followed_ratings:
            return {}
        
        song_weighted_ratings = defaultdict(list)
        for song_id, rating, timestamp in followed_ratings:
            song_weighted_ratings[song_id].append((rating, timestamp))
        
        song_scores_raw = {}
        for song_id, ratings in song_weighted_ratings.items():
            weighted_sum = sum(
                rating * self._apply_time_decay(timestamp, self.rating_half_life)
                for rating, timestamp in ratings
            )
            total_weight = sum(self._apply_time_decay(timestamp, self.rating_half_life) for _, timestamp in ratings)
            
            if total_weight > 0:
                song_scores_raw[song_id] = (weighted_sum / total_weight - 6) / 4
        
        song_details = db.session.query(
            Song.id, Song.artist_name, Song.track_name
        ).filter(Song.id.in_(song_scores_raw.keys())).all()
        
        song_scores = {
            song_id: song_scores_raw[song_id]
            for song_id, artist, title in song_details
            if (artist, self._normalize_title(title)) not in rated_artist_title_pairs
        }
        
        return song_scores
    
    def _ensure_enhanced_diversity(self, sorted_song_scores, limit):
        """
        Optimized diversity filter with cached song info
        """
        artist_count = defaultdict(int)
        artist_titles = defaultdict(set)
        album_count = defaultdict(int)
        diverse_recommendations = []
        
        song_info = {
            s.id: {
                'artist': s.artist_name,
                'title': s.track_name,
                'norm_title': self._normalize_title(s.track_name),
                'album': s.album_name
            }
            for s in db.session.query(Song.id, Song.artist_name, Song.track_name, Song.album_name)
            .filter(Song.id.in_([song_id for song_id, _ in sorted_song_scores])).all()
        }
        
        for song_id, score in sorted_song_scores:
            if song_id not in song_info:
                continue
                
            info = song_info[song_id]
            artist, norm_title, album = info['artist'], info['norm_title'], info['album']
            
            if norm_title in artist_titles[artist]:
                continue
                
            if artist_count[artist] < 3 and (not album or album_count[album] < 2):
                diverse_recommendations.append((song_id, score))
                artist_count[artist] += 1
                artist_titles[artist].add(norm_title)
                if album:
                    album_count[album] += 1
                
                if len(diverse_recommendations) >= limit:
                    break
        
        if len(diverse_recommendations) < limit:
            for song_id, score in sorted_song_scores:
                if song_id not in [s[0] for s in diverse_recommendations] and song_id in song_info:
                    info = song_info[song_id]
                    if info['norm_title'] not in artist_titles[info['artist']]:
                        diverse_recommendations.append((song_id, score))
                        artist_titles[info['artist']].add(info['norm_title'])
                        if len(diverse_recommendations) >= limit:
                            break
        
        return diverse_recommendations
    
    def _filter_duplicate_versions(self, sorted_song_scores, limit):
        """
        Optimized duplicate version filter
        """
        filtered_recommendations = []
        artist_titles = defaultdict(set)
        
        song_info = {
            s.id: {
                'artist': s.artist_name,
                'norm_title': self._normalize_title(s.track_name)
            }
            for s in db.session.query(Song.id, Song.artist_name, Song.track_name)
            .filter(Song.id.in_([song_id for song_id, _ in sorted_song_scores])).all()
        }
        
        for song_id, score in sorted_song_scores:
            if song_id not in song_info:
                continue
                
            info = song_info[song_id]
            if info['norm_title'] not in artist_titles[info['artist']]:
                filtered_recommendations.append((song_id, score))
                artist_titles[info['artist']].add(info['norm_title'])
                if len(filtered_recommendations) >= limit:
                    break
        
        return filtered_recommendations
    
    def generate_for_user(self, user_id, limit=10):
        """
        Generate diverse recommendations
        """
        rated_song_ids = {r[0] for r in db.session.query(Rating.song_id).filter(Rating.user_id == user_id).all()}
        rated_artist_title_pairs = {
            (artist, self._normalize_title(title))
            for artist, title in db.session.query(Song.artist_name, Song.track_name).filter(Song.id.in_(rated_song_ids)).all()
        }
        
        song_scores = defaultdict(float)
        
        for source, weight in [
            (self._get_balanced_artist_preferences(user_id, rated_artist_title_pairs), 'artist_preference'),
            (self._get_album_preferences(user_id, rated_artist_title_pairs), 'album_preference'),
            (self._get_popular_songs(rated_song_ids, rated_artist_title_pairs), 'popular_songs'),
            (self._get_view_based_recommendations(user_id, rated_song_ids, rated_artist_title_pairs), 'view_history'),
            (self._get_social_recommendations(user_id, rated_song_ids, rated_artist_title_pairs), 'social')
        ]:
            for song_id, score in source.items():
                song_scores[song_id] += score * self.weights[weight]
        
        max_score = max(song_scores.values(), default=1.0)
        if max_score > 0:
            song_scores = {k: v/max_score for k, v in song_scores.items()}
            
        sorted_songs = sorted(song_scores.items(), key=lambda x: x[1], reverse=True)
        diverse_recommendations = self._ensure_enhanced_diversity(sorted_songs, limit)
        
        self._store_recommendations(user_id, diverse_recommendations, "diverse")
        return diverse_recommendations
    
    def generate_pure_recommendations(self, user_id, limit=10):
        """
        Generate recommendations without strict diversity
        """
        rated_song_ids = {r[0] for r in db.session.query(Rating.song_id).filter(Rating.user_id == user_id).all()}
        rated_artist_title_pairs = {
            (artist, self._normalize_title(title))
            for artist, title in db.session.query(Song.artist_name, Song.track_name).filter(Song.id.in_(rated_song_ids)).all()
        }
        
        song_scores = defaultdict(float)
        
        for source, weight in [
            (self._get_balanced_artist_preferences(user_id, rated_artist_title_pairs), 'artist_preference'),
            (self._get_album_preferences(user_id, rated_artist_title_pairs), 'album_preference'),
            (self._get_popular_songs(rated_song_ids, rated_artist_title_pairs), 'popular_songs'),
            (self._get_view_based_recommendations(user_id, rated_song_ids, rated_artist_title_pairs), 'view_history'),
            (self._get_social_recommendations(user_id, rated_song_ids, rated_artist_title_pairs), 'social')
        ]:
            for song_id, score in source.items():
                song_scores[song_id] += score * self.weights[weight]
        
        sorted_songs = sorted(song_scores.items(), key=lambda x: x[1], reverse=True)
        filtered_recommendations = self._filter_duplicate_versions(sorted_songs, limit)
        
        self._store_recommendations(user_id, filtered_recommendations, "pure")
        return filtered_recommendations
    
    def _store_recommendations(self, user_id, recommendations, rec_type="diverse"):
        """
        Optimized storage with bulk operations
        """
        existing_recs = {song_id: rec_id for song_id, rec_id in db.session.query(
            Recommendation.song_id, Recommendation.id
        ).filter(Recommendation.user_id == user_id).all()}
        
        new_song_ids = {song_id for song_id, _ in recommendations}
        
        updates = [
            {"id": existing_recs[song_id], "recommendation_score": float(score)}
            for song_id, score in recommendations
            if song_id in existing_recs
        ]
        if updates:
            db.session.bulk_update_mappings(Recommendation, updates)
        
        new_recs = [
            {"user_id": user_id, "song_id": song_id, "recommendation_score": float(score)}
            for song_id, score in recommendations
            if song_id not in existing_recs
        ]
        if new_recs:
            db.session.bulk_insert_mappings(Recommendation, new_recs)
        
        to_delete = set(existing_recs.keys()) - new_song_ids
        if to_delete:
            db.session.query(Recommendation).filter(
                Recommendation.user_id == user_id,
                Recommendation.song_id.in_(to_delete)
            ).delete(synchronize_session=False)
        
        db.session.commit()

def get_user_recommendations(user_id, limit=10, diverse=True):
    recommendations = Recommendation.query.filter_by(user_id=user_id).order_by(Recommendation.recommendation_score.desc()).limit(limit).all()
    
    if not recommendations:
        recommender = SongwallRecommender(user_id)
        if diverse:
            recommender.generate_for_user(user_id, limit)
        else:
            recommender.generate_pure_recommendations(user_id, limit)
        
        recommendations = Recommendation.query.filter_by(user_id=user_id).order_by(Recommendation.recommendation_score.desc()).limit(limit).all()
    
    return [(recommendation.song, recommendation.recommendation_score) for recommendation in recommendations]

def update_user_recommendations(user_id, limit=10, diverse=True):
    recommender = SongwallRecommender(user_id)
    if diverse:
        recommender.generate_for_user(user_id, limit)
    else:
        recommender.generate_pure_recommendations(user_id, limit)
    
    return get_user_recommendations(user_id, limit, diverse)

def generate_all_recommendations(diverse=True):
    users = User.query.all()
    
    for user in users:
        try:
            recommender = SongwallRecommender(user.id)
            if diverse:
                recommender.generate_for_user(user.id)
            else:
                recommender.generate_pure_recommendations(user.id)
            print(f"Generated recommendations for user {user.username}")
        except Exception as e:
            print(f"Error generating recommendations for user {user.username}: {e}")
    
    print("Recommendation generation complete")