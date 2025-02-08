// Save email to cookie
function setCookie(name, value, days) {
    const date = new Date();
    date.setTime(date.getTime() + (days * 24 * 60 * 60 * 1000));
    document.cookie = `${name}=${value}; expires=${date.toUTCString()}; path=/`;
}

// Retrieve email from cookie
function getCookie(name) {
    const cookies = document.cookie.split(';');
    for (let cookie of cookies) {
        cookie = cookie.trim();
        if (cookie.startsWith(`${name}=`)) {
            return cookie.substring(name.length + 1);
        }
    }
    return "";
}

// Delete email cookie
function deleteCookie(name) {
    document.cookie = `${name}=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;`;
}

// Auto-fill email on page load
window.onload = function() {
    const savedEmail = getCookie("saved_email");
    if (savedEmail) {
        document.getElementById("email").value = savedEmail;
        document.getElementById("remember_email").checked = true;
    }
};

// Save email on form submission if checkbox is checked
document.addEventListener("DOMContentLoaded", function () {
    const form = document.querySelector(".auth-form");
    if (form) {
        form.addEventListener("submit", function () {
            const rememberEmail = document.getElementById("remember_email").checked;
            const email = document.getElementById("email").value;

            if (rememberEmail) {
                setCookie("saved_email", email, 30); // Save for 30 days
            } else {
                deleteCookie("saved_email"); // Delete cookie if unchecked
            }
        });
    }
});

