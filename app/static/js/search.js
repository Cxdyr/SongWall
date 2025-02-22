document.addEventListener('DOMContentLoaded', function() {
    var searchBar = document.getElementById('search-bar');
    var suggestionsDiv = document.getElementById('suggestions');
    var timeout;

    // Function that converts a song py object to HTML
    function songToHtml(song) {
        return `
            <div class="song2">
                <a href="/rate/${song.spotify_id}">
                    <img src="${song.album_image_url}" alt="Album Art for ${song.name}">
                </a>
                <h3><a href="/search/view/${song.spotify_id}">${song.name}</a></h3>
                <p>${song.artist}</p>
                <p>${song.album_name}</p> <br>
                <a href="${song.spotify_url}" class="btn btn-success spotify-btn" target="_blank">Spotify</a>
            </div>
        `;
    }

    searchBar.addEventListener('input', function() {
        clearTimeout(timeout);
        var query = this.value;

        if (query.length > 0) {
            // Debounce the request to avoid flooding the server, we wait about 300 ms before sending the request
            timeout = setTimeout(function() {
                fetch('/search/suggestions?query=' + encodeURIComponent(query))
                    .then(response => response.json())
                    .then(songs => {
                        if (songs.length === 0) {
                            suggestionsDiv.innerHTML = '<p>Not found. Press search button!</p>';
                        } else {
                            const html = songs.map(songToHtml).join('');
                            suggestionsDiv.innerHTML = `<div class="song-list" id="top-rated-list">${html}</div>`;
                        }
                    })
                    .catch(error => console.error('Error fetching suggestions:', error));
            }, 300);  // 300ms delay for debouncing
        } else {
            suggestionsDiv.innerHTML = '<p>No songs found. Try a search!</p>';
        }
    });
});