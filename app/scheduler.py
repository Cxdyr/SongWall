from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
from app.db_functions import get_popular_songwall_songs, get_top_rated_songs

# Initialize the scheduler
scheduler = BackgroundScheduler()

# Function to update the cache every 24 hours
def update_cached_data():
    global pop_songs_cache, top_rated_songs_cache
    pop_songs_cache = get_popular_songwall_songs(9)
    top_rated_songs_cache = get_top_rated_songs(9)
    print(f"Cache updated at {datetime.now()}")

# Schedule the job
scheduler.add_job(func=update_cached_data, trigger='interval', hours=24)
scheduler.start()

# Keep the script running
if __name__ == "__main__":
    try:
        while True:
            pass
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()