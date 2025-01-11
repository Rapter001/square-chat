## Overview

Square Chat is a sleek and modern web chat application designed for simplicity and efficiency.

---

## Features

- **Real-time Messaging**: Chat with friends and colleagues in real-time.
- **Google Login**: Seamlessly integrate with your Google account for easy login.
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

$ docker run --name square-chat -d -p 5000:5000 -v path:/app/data/ rapter001/square-chat

- Replace `path` in `-v path:/app/data/` with the desired path to save messages, rooms, emails, passwords on the host machine.
- Optionally, remove `-v path:/app/data/` to save messages, rooms, emails, passwords to the Docker container.
- Replace `-p 5000:5000` with `-p 80:5000` to change the port to port 80 or with any other desired port.

---

## Usage

To use Square Chat, follow these steps:

### Step 1: Create OAuth 2.0 Credentials on Google Cloud Console

1. **Open Your Web Browser**.
2. **Navigate to the Google Cloud Console**:

   - `https://console.cloud.google.com/`
3. **Create a New Project**:

   - Click on the "Select a project" dropdown menu.
   - Click on "New Project".
   - Enter a project name and click on "Create".
4. **Enable the Google Sign-In API**:

   - Navigate to the API Library page.
   - Search for "Google Sign-In API".
   - Click on the result, then click on the "Enable" button.
5. **Create OAuth 2.0 Credentials**:

   - Navigate to the API Credentials page.
   - Click on "Create Credentials" and select "OAuth client ID".
   - Select "Web application" and enter a authorized JavaScript origins.
   - Click on "Create" and copy the Client ID and Client secret.

### Step 2: Configure OAuth 2.0 Credentials for Square Chat

1. **Create a .env File**:

   - Create a new file named `.env` in the root directory of your project.
   - Add the following lines to the file:

     ```
     google_oauth_client_id=your_client_id
     google_oauth_client_secret=your_client_secret
     ```
   - Replace `your_client_id` and `your_client_secret` with the values you copied in Step 1.
2. **Configure Docker Environment Variables**:

   - Alternatively, you can configure the environment variables in your Docker container.
   - Add the following lines to your `docker run` command:

     ```
     -e google_oauth_client_id=your_client_id
     -e google_oauth_client_secret=your_client_secret
     ```
   - Replace `your_client_id` and `your_client_secret` with the values you copied in Step 1.

### Step 3: Run Square Chat

1. **Run the Docker Container**:

   - Follow the instructions in the [Installation](#installation) section to run the Docker container.
2. **Access Square Chat**:

   - Open your web browser and navigate to `http://127.0.0.1:5000` or `http://localhost:5000`.
- You should now be able to use Google Sign-In with Square Chat.
- If you need help, join my Discord at: <a href="https://rapter.pages.dev/links">https://rapter.pages.dev/links</a>
____________________________________________________

## Acknowledgments

Square Chat is a work in progress, and improvements are continually being made. Thank you for your patience and support as we strive to provide the best chatting experience possible.
