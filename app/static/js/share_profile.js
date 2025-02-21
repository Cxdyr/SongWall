document.addEventListener('DOMContentLoaded', function() {
    const shareButton = document.getElementById('copy-share-link');
    if (shareButton) {
        shareButton.addEventListener('click', function() {
            const shareLink = shareButton.dataset.shareLink;
            navigator.clipboard.writeText(shareLink)
                .then(() => {
                    alert('Link copied to clipboard!');
                })
                .catch(err => {
                    console.error('Failed to copy: ', err);
                    alert('Failed to copy link. Please try again.');
                });
        });
    }
});
