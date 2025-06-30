document.addEventListener("DOMContentLoaded", () => {
    const socket = io();
    const currentUserId = document.body.dataset.userId;

    // Join notification room for the current user
    socket.emit('join', { room_id: `notifications_${currentUserId}` });

    // Handle join request notifications
    socket.on('join_request_received', (data) => {
        showNotification(`New join request for ${data.room_name} from ${data.user_name}`, 'info');
    });

    // Handle join request status updates
    socket.on('join_request_status', (data) => {
        const status = data.status;
        const roomName = data.room_name;
        if (status === 'approved') {
            showNotification(`Your request to join ${roomName} has been approved!`, 'success');
            // Reload the page to update the room access
            setTimeout(() => window.location.reload(), 2000);
        } else if (status === 'rejected') {
            showNotification(`Your request to join ${roomName} has been rejected.`, 'error');
            // Re-enable the join button
            const joinBtn = document.querySelector(`[data-room-id="${data.room_id}"]`);
            if (joinBtn) {
                joinBtn.textContent = 'Request to Join';
                joinBtn.disabled = false;
                joinBtn.classList.remove('bg-gray-400', 'cursor-not-allowed');
            }
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

    // Copy invite link functionality
    function copyInviteLink(inviteCode) {
        const baseUrl = window.location.origin;
        const inviteLink = `${baseUrl}/join/${inviteCode}`;
        
        navigator.clipboard.writeText(inviteLink).then(() => {
            showNotification('Invite link copied to clipboard!', 'success');
        }).catch(err => {
            console.error('Failed to copy invite link:', err);
            showNotification('Failed to copy invite link', 'error');
        });
    }

    // Notification system
    function showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `fixed bottom-6 right-6 p-4 rounded-lg shadow-lg text-white z-50 ${
            type === 'success' ? 'bg-green-500' : type === 'error' ? 'bg-red-500' : 'bg-blue-500'
        }`;
        notification.textContent = message;
        document.body.appendChild(notification);
        setTimeout(() => notification.remove(), 4000);
    }

    // Add fade-in animation to room cards
    const roomCards = document.querySelectorAll('.room-card');
    roomCards.forEach((card, index) => {
        card.classList.add('animate-fade-in-down');
        card.style.animationDelay = `${index * 0.1}s`;
    });
}); 