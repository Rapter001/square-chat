document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('createRoomForm');
    const isPrivateCheckbox = document.getElementById('is_private');
    const privateRoomOptions = document.getElementById('privateRoomOptions');

    // Show/hide private room options
    isPrivateCheckbox.addEventListener('change', function() {
        privateRoomOptions.classList.toggle('hidden', !this.checked);
    });

    // Form submission
    form.addEventListener('submit', async function(e) {
        e.preventDefault();

        const roomData = {
            name: document.getElementById('roomName').value,
            description: document.getElementById('roomDescription').value,
            is_private: isPrivateCheckbox.checked
        };

        try {
            const response = await fetch('/create_room', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(roomData)
            });

            if (response.ok) {
                window.location.href = '/rooms';
            } else {
                const error = await response.json();
                alert(error.error || 'Failed to create room');
            }
        } catch (error) {
            console.error('Error:', error);
            alert('Failed to create room');
        }
    });

    // Theme toggle functionality
    const themeToggle = document.getElementById('themeToggle');
    const prefersDarkScheme = window.matchMedia('(prefers-color-scheme: dark)');

    // Check for saved theme preference or use system preference
    const currentTheme = localStorage.getItem('theme');
    if (currentTheme === 'dark' || (!currentTheme && prefersDarkScheme.matches)) {
        document.body.classList.add('dark-mode');
        themeToggle.checked = true;
    }

    themeToggle.addEventListener('change', function() {
        if (this.checked) {
            document.body.classList.add('dark-mode');
            localStorage.setItem('theme', 'dark');
        } else {
            document.body.classList.remove('dark-mode');
            localStorage.setItem('theme', 'light');
        }
    });

    // Mobile menu toggle
    function toggleMobileMenu() {
        const navLinks = document.querySelector('.nav-links');
        navLinks.classList.toggle('active');
    }
}); 