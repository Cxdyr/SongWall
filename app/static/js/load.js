document.addEventListener('DOMContentLoaded', () => {
  const genreButtons = document.querySelectorAll('.genre-btn');
  const songCarousel = document.getElementById('genre-song-list');
  // Get the base URL for viewing a song (should be something like "/view_song/")
  const viewSongBase = songCarousel.getAttribute('data-view-url');

  genreButtons.forEach(button => {
    button.addEventListener('click', (e) => {
      e.preventDefault(); // Prevent the default page reload

      // Update active button styling
      genreButtons.forEach(btn => btn.classList.remove('active'));
      e.currentTarget.classList.add('active');

      // Extract the genre from the button text (to lowercase)
      let genre = e.currentTarget.textContent.toLowerCase();
      // Build the URL for AJAX fetching; encode the genre
      const url = `/genre_songs/${encodeURIComponent(genre)}`;

      // Fetch the new songs via AJAX
      fetch(url)
        .then(response => response.json())
        .then(data => {
          if (data.songs && data.songs.length > 0) {
            let html = '<div class="song-list">';
            data.songs.forEach(song => {
              html += `
                <div class="song2">
                  <a href="${viewSongBase}${song.id}">
                    <img src="${song.album_image}" alt="Album Art for ${song.track_name}">
                  </a>
                  <h3>
                    <a href="${viewSongBase}${song.id}">${song.track_name}</a>
                  </h3>
                  <p>${song.artist_name}</p>
                  <p>${song.album_name}</p>
                </div>
              `;
            });
            html += '</div>';
            songCarousel.innerHTML = html;
          } else {
            songCarousel.innerHTML = `<p>No songs found for ${genre}.</p>`;
          }
        })
        .catch(error => {
          console.error('Error fetching songs:', error);
          songCarousel.innerHTML = `<p>Error loading songs. Please try again later.</p>`;
        });
    });
  });
});

