from flask import Flask, app, render_template, request, jsonify
from songwall_search import search_songs
from songwall_popular_songs import get_popular_songs


app = Flask(__name__)


@app.route('/')
def index():
    return render_template('index.html')

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5000)