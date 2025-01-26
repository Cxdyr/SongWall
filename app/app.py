from flask import Flask, app, render_template, request, jsonify
from songwall_search import search_songs
from songwall_popular_songs import get_popular_songs


app = Flask(__name__)

#pop_songs = get_popular_songs()   # In implementation this will need to be in a nested function that calls all once daily population operations once a day on a 24hr time loop, for dev we have it here


@app.route('/')
def index():
    return render_template('index.html')

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5000)