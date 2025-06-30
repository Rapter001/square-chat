document.addEventListener("DOMContentLoaded", () => {
    // ==============================
    // Theme Toggle Logic
    // ==============================
    const toggle = document.getElementById("themeToggle");
    const prefersDarkScheme = window.matchMedia('(prefers-color-scheme: dark)');

    // Check for saved theme preference or use system preference
    const currentTheme = localStorage.getItem('theme');
    if (currentTheme === 'dark' || (!currentTheme && prefersDarkScheme.matches)) {
        document.documentElement.classList.add("dark-mode");
        if (toggle) toggle.checked = true;
    }

    // Toggle theme on checkbox change
    if (toggle) {
        toggle.addEventListener("change", () => {
            if (toggle.checked) {
                document.documentElement.classList.add("dark-mode");
                localStorage.setItem("theme", "dark");
            } else {
                document.documentElement.classList.remove("dark-mode");
                localStorage.setItem("theme", "light");
            }
        });
    }

    // ==============================
    // Chat Logic with Socket.IO
    // ==============================
    const socket = io();
    const messageForm = document.getElementById("messageForm");
    const messageInput = document.getElementById("messageInput");
    const messagesContainer = document.getElementById("messages");
    const memberCountEl = document.querySelector("#memberCount .count");

    const urlParams = new URLSearchParams(window.location.search);
    const roomId = urlParams.get("room_id");
    const room = roomId || null;

    // Initialize timestamps for existing messages
    function initializeTimestamps() {
        document.querySelectorAll(".timestamp").forEach((el) => {
            const ts = el.dataset.timestamp;
            if (ts) el.textContent = formatTimeAgo(ts);
        });
    }

    // Function to scroll to bottom
    function scrollToBottom() {
        const messagesContainer = document.getElementById("messages");
        if (messagesContainer) {
            // Use requestAnimationFrame to ensure smooth scrolling
            requestAnimationFrame(() => {
                messagesContainer.scrollTop = messagesContainer.scrollHeight;
            });
        }
    }

    // Initialize timestamps and scroll to bottom after content is loaded
    window.addEventListener('load', () => {
        initializeTimestamps();
        scrollToBottom();
    });

    // Join room
    socket.emit("join", { room_id: room });

    // Submit new message
    if (messageForm) {
        messageForm.addEventListener("submit", (e) => {
            e.preventDefault();
            const message = messageInput.value.trim();
            if (message !== "") {
                socket.emit("message", { room: room, message }, (response) => {
                    if (response && response.error) {
                        console.error("Error sending message:", response.error);
                    }
                });
                messageInput.value = "";
                isUserScrolled = false;
                scrollToBottom();
            }
        });
    }

    // Receive message
    socket.on("message", (data) => {
        if (data && !data.error) {
            appendMessage(data);
            if (shouldAutoScroll()) {
                scrollToBottom();
            }
        }
    });

    // Update member count
    socket.on("member_count", (data) => {
        if ((room && data.room_id == room) || (!room && data.room_id === "public")) {
            if (memberCountEl) memberCountEl.textContent = data.count;
        }
    });

    // Append a new message
    function appendMessage(data) {
        const div = document.createElement("div");
        div.classList.add("message");
        const profileImg = data.profile_img ? data.profile_img : '/static/img/default-profile.png';
        div.innerHTML = `
            <div class="flex items-start">
                <img class="h-8 w-8 rounded-full mr-3" src="${profileImg}" alt="${data.name}">
                <div class="flex-1">
                    <div class="flex items-center">
                        <span class="font-semibold text-primary">${data.name}</span>
                        <span class="ml-2 text-xs text-secondary timestamp" data-timestamp="${data.created_at}">${formatTimeAgo(data.created_at)}</span>
                    </div>
                    <p class="text-secondary">${escapeHTML(data.message)}</p>
                </div>
            </div>
        `;
        messagesContainer.appendChild(div);
        
        // Use requestAnimationFrame to ensure the DOM is updated before scrolling
        requestAnimationFrame(() => {
            if (shouldAutoScroll()) {
                scrollToBottom();
            }
        });
    }

    // Add auto-scroll functionality
    let isUserScrolled = false;
    let lastScrollTop = 0;

    function shouldAutoScroll() {
        const messagesContainer = document.getElementById("messages");
        if (!messagesContainer) return false;
        
        const currentScrollTop = messagesContainer.scrollTop;
        const scrollHeight = messagesContainer.scrollHeight;
        const clientHeight = messagesContainer.clientHeight;
        
        // If we're within 100px of the bottom, consider it "at bottom"
        return currentScrollTop + clientHeight >= scrollHeight - 100;
    }

    messagesContainer.addEventListener('scroll', () => {
        const currentScrollTop = messagesContainer.scrollTop;
        const scrollHeight = messagesContainer.scrollHeight;
        const clientHeight = messagesContainer.clientHeight;
        
        // If user scrolls up, pause auto-scroll
        if (currentScrollTop < lastScrollTop) {
            isUserScrolled = true;
        }
        // If user scrolls to bottom, resume auto-scroll
        else if (currentScrollTop + clientHeight >= scrollHeight - 100) {
            isUserScrolled = false;
        }
        
        lastScrollTop = currentScrollTop;
    });

    // Timestamp formatting
    function formatTimeAgo(isoTimestamp) {
        if (!isoTimestamp) return "";
        const date = new Date(isoTimestamp);
        const seconds = Math.floor((new Date() - date) / 1000);
        if (seconds < 60) return "Just now";
        if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
        if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
        return `${Math.floor(seconds / 86400)}d ago`;
    }

    // Escape HTML for safety
    function escapeHTML(str) {
        return str.replace(/[&<>"']/g, tag => ({
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#39;',
        }[tag]));
    }

    // Update timestamps every minute
    setInterval(() => {
        document.querySelectorAll(".timestamp").forEach((el) => {
            const ts = el.dataset.timestamp;
            if (ts) el.textContent = formatTimeAgo(ts);
        });
    }, 60000);
});
