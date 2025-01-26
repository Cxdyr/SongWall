from flask import Flask, app, render_template, request, jsonify
from songwall_search import search_songs


@app.route('/')
def index():
    return render_template('index.htmml')

if __name__ == "__main__":
    app.run(debub=True, host='0.0.0.0', port=5000)