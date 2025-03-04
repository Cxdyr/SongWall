from datetime import datetime, timedelta, timezone
import threading
from app.db_functions import get_recent_songs, get_top_rated_songs
from app.songwall_recommendations import generate_all_recommendations, update_user_recommendations

# Global cache variables
recent_songs_cache = None
top_rated_songs_cache = None
last_cache_update = None
last_recommendation_update = None
cache_lock = threading.Lock()  # Lock to prevent concurrent cache updates (SAFETY!!)
recommendation_lock = threading.Lock()  # Lock for recommendation updates

def update_cached_data(app):
    """
    Updates the popular and top-rated songs caches by querying the database, used for efficient caching
    """
    global recent_songs_cache, top_rated_songs_cache
    with app.app_context():
        recent_songs_cache = get_recent_songs(10)
        top_rated_songs_cache = get_top_rated_songs(10)
        print(f"Cache updated at {datetime.now(timezone.utc)}")

def initialize_cache(app):
    """
    Initialize the cache on the first page load or if cache is empty.
    """
    global recent_songs_cache, top_rated_songs_cache
    if not recent_songs_cache or not top_rated_songs_cache:
        update_cached_data(app)

def update_cache_if_needed(app):
    """
    This function checks if the cache needs to be updated.
    - Song cache updates every hour
    - Recommendation cache updates every 24 hours
    - Uses locks to ensure only one update occurs at a time.
    """
    global last_cache_update
    one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)

    # Only attempt to update the song cache if it hasn't been updated in the last hour
    if last_cache_update is None or last_cache_update < one_hour_ago:
        # get the lock to prevent multiple threads from updating the cache
        if cache_lock.acquire(blocking=False):
            try:
                # Update song cache (hourly)
                update_cached_data(app)
                last_cache_update = datetime.now(timezone.utc)
                
                # Check if recommendations need updating (daily)
                update_all_recommendations_if_needed(app)
            finally:
                cache_lock.release()  # Release the lock after updating
        else:
            print("Cache update already in progress. Skipping update.")
            

def update_all_recommendations_if_needed(app):
    """
    This function checks if global recommendations need to be updated.
    - If recommendations have not been updated for more than 24 hours, we will refresh them.
    - Uses a lock to ensure only one update occurs at a time.
    """
    global last_recommendation_update
    one_day_ago = datetime.now(timezone.utc) - timedelta(days=1)

    # Only attempt to update recommendations if they haven't been updated in the last 24 hours
    if last_recommendation_update is None or last_recommendation_update < one_day_ago:
        # Get the lock to prevent multiple threads from updating recommendations
        if recommendation_lock.acquire(blocking=False):
            try:
                with app.app_context():
                    # Generate recommendations for all users
                    print(f"Generating recommendations for all users at {datetime.now(timezone.utc)}")
                    generate_all_recommendations()  # Generate recommendations for all users
                    print(f"Recommendations updated at {datetime.now(timezone.utc)}")
                    last_recommendation_update = datetime.now(timezone.utc)
            except Exception as e:
                print(f"Error updating all recommendations: {e}")
            finally:
                recommendation_lock.release()  # Release the lock after updating
        else:
            print("Recommendation update already in progress. Skipping update.")

def get_cached_songs():
    """
    Return the cached songs.
    """
    return recent_songs_cache, top_rated_songs_cache
