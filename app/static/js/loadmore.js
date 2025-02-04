document.getElementById('load-more').addEventListener('click', function () {
    let button = this;
    let offset = parseInt(button.getAttribute('data-offset'));

    fetch(`/load_more_posts?offset=${offset}`)
        .then(response => response.json())
        .then(data => {
            let container = document.getElementById('posts-container');
            data.forEach(post => {
                let postElement = document.createElement('div');
                postElement.classList.add('post');

                // Use the profile URL and song ID from the data
                let profileUrl = post.profile_url;  // The URL for the profile
                let songUrl = `/view/${post.song_id}`;  // The URL for the song using the song ID

                postElement.innerHTML = `
                    <div class="post-left">
                        <a href="${profileUrl}" class="username-link"><strong>${post.username}</strong></a>
                        <p class="post-song"><a href="${songUrl}">🎵 ${post.song_name} - ${post.artist_name}</a></p>
                    </div>
                    <div class="post-right">
                        <p class="post-message">${post.post_message}</p>
                        <p class="timestamp">${post.timestamp}</p>
                    </div>
                `;

                container.appendChild(postElement);
            });

            offset += 10;
            button.setAttribute('data-offset', offset);

            if (data.length < 10) {
                button.style.display = 'none';  // Hide the button if there are less than 10 posts
            }
        })
        .catch(error => {
            console.error("Error loading more posts:", error);
        });
});