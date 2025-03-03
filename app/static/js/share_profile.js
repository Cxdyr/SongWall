document.addEventListener('DOMContentLoaded', function() {
    const shareButton = document.getElementById('copy-share-link');
    if (shareButton) {
        shareButton.addEventListener('click', function() {
            const shareLink = shareButton.dataset.shareLink;
            
            // Fallback method for mobile devices
            if (navigator.share) {
                navigator.share({
                    title: 'Check out my Songwall profile',
                    url: shareLink
                }).catch(console.error);
            } else {
                // Clipboard API fallback
                try {
                    navigator.clipboard.writeText(shareLink).then(() => {
                        alert('Link copied to clipboard!');
                    }).catch(err => {
                        // Fallback method if clipboard fails
                        fallbackCopyTextToClipboard(shareLink);
                    });
                } catch (err) {
                    // Another fallback method if clipboard API is not supported
                    fallbackCopyTextToClipboard(shareLink);
                }
            }
        });
    }

    // Fallback method for copying text
    function fallbackCopyTextToClipboard(text) {
        const textArea = document.createElement("textarea");
        textArea.value = text;
        
        // Avoid scrolling to bottom
        textArea.style.top = "0";
        textArea.style.left = "0";
        textArea.style.position = "fixed";

        document.body.appendChild(textArea);
        textArea.focus();
        textArea.select();

        try {
            const successful = document.execCommand('copy');
            const msg = successful ? 'Link copied to clipboard!' : 'Unable to copy';
            alert(msg);
        } catch (err) {
            alert('Unable to copy link');
        }

        document.body.removeChild(textArea);
    }
});