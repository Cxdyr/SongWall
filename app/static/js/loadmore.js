document.getElementById('load-more').addEventListener('click', function () {
    let button = this;
    let offset = parseInt(button.getAttribute('data-offset'));
    
    console.log('Loading more posts with offset:', offset);
    
    fetch(`/load_more_posts?offset=${offset}`)
        .then(response => {
            console.log('Response status:', response.status);
            return response.json();
        })
        .then(data => {
            console.log('Received posts:', data);
            
            let container = document.getElementById('posts-container');
            
            if (data.length === 0) {
                console.log('No more posts to load');
                button.style.display = 'none';
                return;
            }
            
            data.forEach(post => {
                let postElement = document.createElement('div');
                postElement.classList.add('post');
                
                let profileUrl = post.profile_url;
                let songUrl = `/view/${post.song_id}`;
                
                // Use same structure as the HTML template, now with dynamic theme color
                postElement.innerHTML = `
                    <div class="post-left">
                        <div class="author-avatar" style="--profile-accent: ${post.theme_color};">
                            <span>${post.username[0].toUpperCase()}</span>
                        </div>
                        <a href="${profileUrl}">${post.username}</a>
                        <p class="post-song">
                            <a href="${songUrl}">
                                🎵 ${post.song_name} - ${post.artist_name}
                            </a>
                        </p>
                    </div>
                    <div class="post-right">
                        <p class="post-message">${post.post_message}</p>
                        <p class="timestamp">${formatTimestamp(post.timestamp)}</p>
                    </div>
                `;
                
                container.appendChild(postElement);
            });
            
            offset += 10;
            button.setAttribute('data-offset', offset);
            
            if (data.length < 10) {
                console.log('Less than 10 posts loaded, hiding load more button');
                button.style.display = 'none';
            } else {
                // Move the button to always be at the end
                container.appendChild(button);
            }
        })
        .catch(error => {
            console.error("Error loading more posts:", error);
            // Optional: Show an error message to the user
            alert('Failed to load more posts. Please try again.');
        });
});

// Helper function to format timestamp
function formatTimestamp(timestamp) {
    // Assuming timestamp is in "YYYY-MM-dd HH:MM:SS" format
    return timestamp.split(' ')[0];
}

document.getElementById("toggle-post-form").addEventListener("click", function () {
    let formContainer = document.getElementById("post-form-container");
    let toggleButton = document.getElementById("toggle-post-form");
    
    formContainer.style.display = "block"; // Show the form
    toggleButton.style.display = "none";  // Hide the "Post +" button
});