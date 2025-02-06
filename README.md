<img src="https://raw.githubusercontent.com/Rapter001/square-chat/refs/heads/main/static/img/square-chat.png" alt="Square Chat Logo" width="150" height="150">

# Square Chat - Real-time Web Chat Application

## Overview

Square Chat is a sleek and modern web chat application designed for simplicity and efficiency.

- - -

## Features

* **Real-time Messaging**: Chat with friends and colleagues in real-time.
* **Google Login**: Seamlessly integrate with your Google account for easy login.
* **User-friendly Interface**: Simple and intuitive interface for easy navigation.
* **File Sharing (Coming Soon)**: Share files effortlessly with other users.

- - -

## Tools & Software Used

![images](https://skillicons.dev/icons?i=python,flask,html,css,js,docker)

- - -

## Installation

To install Square Chat, follow these steps:

### 1. **Pull the Docker Image**:

``` bash
$ docker pull rapter001/square-chat:latest
```

### 2. **Run the Docker Container**:

``` bash
$ docker run --name square-chat -d -p 5000:5000 -v path:/app/data/ rapter001/square-chat
```

* Replace `path` in `-v path:/app/data/` with the desired path to save messages, rooms, emails, and passwords on the host machine.
* Optionally, remove `-v path:/app/data/` to save messages, rooms, emails, and passwords to the Docker container.
* Replace `-p 5000:5000` with `-p 80:5000` to change the port to port 80 or with any other desired port.

- - -

## Usage

### Step 1: **Create OAuth 2.0 Credentials on Google Cloud Console**

1. **Open Your Web Browser**.
2. **Navigate to the Google Cloud Console**:
`https://console.cloud.google.com/`
3. **Create a New Project**:
    * Click on the "Select a project" dropdown menu.
    * Click on "New Project".
    * Enter a project name and click on "Create".
4. **Enable the Google Sign-In API**:
    * Navigate to the API Library page.
    * Search for "Google Sign-In API".
    * Click on the result, then click on the "Enable" button.
5. **Create OAuth 2.0 Credentials**:
    * Navigate to the API Credentials page.
    * Click on "Create Credentials" and select "OAuth client ID".
    * Select "Web application" and enter an authorized JavaScript origin.
    * Click on "Create" and copy the Client ID and Client Secret.

### Step 2: **Configure OAuth 2.0 Credentials for Square Chat**

1. **Create a .env File**:
    * Create a new file named `.env` in the root directory of your project.
    * Add the following lines to the file:

    ```
    google_oauth_client_id=your_client_id
google_oauth_client_secret=your_client_secret
    ```

    * Replace `your_client_id` and `your_client_secret` with the values you copied in Step 1.
2. **Configure the Authorized Redirect URIs**:
    * **Local Setup**: If you are running Square Chat locally, the authorized redirect URI in the Google Cloud Console must be configured as:

    ```
    http://localhost:5000/login/authorized
    ```

    If using a different port, replace `5000` with your specific port (e.g., `http://localhost:8080/login/authorized`).
    * **Domain Setup**: If you're using a domain, the authorized redirect URI must be:

    ```
    http://your-domain-name:5000/login/authorized
    ```

    or
        * without any ports for port 80 like http://chat.rapter.pro/login/authorized
        Replace `your-domain-name` with your actual domain, and `5000` with the port Square Chat is running on (e.g., `http://mydomain.com:8080/login/authorized`).
    * Make sure to add `/login/authorized` at the end of the URL in the Google Cloud Console, regardless of whether you are using `localhost` or a domain.
3. **Configure Docker Environment Variables** (Optional):
    * Alternatively, you can configure the environment variables directly in the Docker container.
    * Add the following lines to your `docker run` command:

    ```
    -e google_oauth_client_id=your_client_id
-e google_oauth_client_secret=your_client_secret
    ```

    * Replace `your_client_id` and `your_client_secret` with the values you copied in Step 1.

### Step 3: **Run Square Chat**

1. **Run the Docker Container**:
    * Follow the instructions in the [Installation](#installation) section to run the Docker container.
2. **Access Square Chat**:
    * Open your web browser and navigate to `http://127.0.0.1:5000` or `http://localhost:5000` if you are running the app locally.
    * If you are using a domain, navigate to the domain’s URL (e.g., `http://mydomain.com:5000`).
    * You should now be able to use Google Sign-In with Square Chat.

### Using Docker Compose V2

1. **Verify Docker Compose V2 Installation**:
Ensure you have Docker Compose V2 installed. It's included by default in Docker Desktop and can be installed as part of Docker Engine on Linux.
Check your installation by running:

``` bash
docker compose version
```

2. **Running with Docker Compose V2**:
With Docker Compose V2, the command syntax has changed slightly. Use `docker compose` (note the space) instead of `docker-compose` go to docker compose offical documentation to install Docker Compose V2 [https://docs.docker.com/compose/](https://docs.docker.com/compose/).
    * To start the services:

    ``` bash
    docker compose up -d
    ```

    * To stop the services:

    ``` bash
    docker compose down
    ```

    * To rebuild and restart the services:

    ``` bash
    docker compose up --build
    ```

- - -

## Acknowledgments

Square Chat is a work in progress, and improvements are continually being made. Thank you for your patience and support as we strive to provide the best chatting experience possible.

If you need help, join my Discord at: [Rapter Links](https://rapter.pages.dev/links)