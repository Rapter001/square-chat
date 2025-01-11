## Overview

Square Chat is a sleek and modern web chat application designed for simplicity and efficiency.

---

## Features

- **Real-time Messaging**: Chat with friends and colleagues in real-time.
- **Private room chat**: Chat with friends and colleagues in private rooms
- **User-friendly Interface**: Simple and intuitive interface for easy navigation.
- **File Sharing (Coming Soon)**: Share files effortlessly with other users.

---

## Tools & Software Used

![images](https://skillicons.dev/icons?i=python,flask,html,css,js,docker)

---

## Installation

To install Square Chat, follow these steps:

1. **Pull the Docker Image**:

$ docker pull rapter001/square-chat:latest

2. **Run the Docker Container**:

$ docker run --name square-chat -d -p 5000:5000 -v path:/app/files/ rapter001/square-chat

- Replace `path` in `-v path:/app/instance/` with the desired path to save messages, rooms, emails, passwords on the host machine.
- Optionally, remove `-v path:/app/instance/` to save messages, rooms, emails, passwords to the Docker container.
- Replace `-p 5000:5000` with `-p 80:5000` to change the port to port 80 or with any other desired port.

---

## Usage

To use Square Chat, follow these steps:

1. **Open Your Web Browser**.
2. **Navigate to the Following URL**:

- `http://127.0.0.1:5000`
- `http://localhost:5000`
- `http://your-computers-ip:5000`
- https://chat.rapter.pro

---

## Acknowledgments

Square Chat is a work in progress, and improvements are continually being made. Thank you for your patience and support as we strive to provide the best chatting experience possible.
