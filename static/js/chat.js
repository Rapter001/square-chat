const socket = io.connect();
const chatbox = document.getElementById('chatbox');
const messageInput = document.getElementById('message');

// Get user’s time zone
const userTimezone = Intl.DateTimeFormat().resolvedOptions().timeZone;

// Scroll to the bottom when new messages are received
socket.on('message', (data) => {
    const messageElement = document.createElement('div');
    messageElement.classList.add('message');
    messageElement.innerHTML = `
        <img src="${data.profile_img}" alt="${data.name}">
        <div class="message-content">
            <div class="name">${data.name}</div>
            <div class="text">${data.message}</div>
            <div class="timestamp">${data.user_local_time}</div>
        </div>
    `;
    chatbox.appendChild(messageElement);
    chatbox.scrollTop = chatbox.scrollHeight;
});

// Function to send a message
function sendMessage() {
    const message = messageInput.value;
    if (message.trim() !== "") {
        socket.emit('send_message', { message, timezone: userTimezone });
        messageInput.value = '';
    }
}

messageInput.addEventListener('keydown', (event) => {
    if (event.key === 'Enter') {
        event.preventDefault();
        sendMessage();
    }
});

window.onload = () => {
    chatbox.scrollTop = chatbox.scrollHeight;
};