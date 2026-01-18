# Flashcards Study Tool

A lightweight, interactive web application for creating and studying flashcards. Built with a Flask backend and a React frontend, this tool allows you to build your own knowledge base and study on any device connected to your local network.

> **Live Demo:** You can check if the app is currently running live at [https://funtimezallaround.eu.pythonanywhere.com/](https://funtimezallaround.eu.pythonanywhere.com/).

## Features

*   **User Authentication**: Secure Login and Registration system ensures your cards are private and saved to your account.
*   **Hierarchical Topic System**:
    *   **Nested Topics**: Create folders within folders (sub-topics) with unlimited depth to organize your study materials.
    *   **Drag-and-Drop Organization**: Easily reorder content or move topics between parents using an intuitive drag-and-drop interface.
    *   **Smart Navigation**: The app remembers your last visited topic, so you pick up right where you left off.
    *   **Full Control**: Includes a default "My Flashcards" topic that behaves just like any other—rename or delete it as you see fit.
*   **Interactive Study Mode**: Smooth card flipping animations and navigation (Next/Previous).
*   **Card Management**:
    *   **Create**: Add new cards with a Front (Question) and Back (Answer), assigned to specific topics.
    *   **Recursive Learning**: Studying a parent topic automatically includes cards from all its sub-topics.
    *   **Delete**: Remove cards you no longer need.
    *   **Import**: Bulk upload cards using a JSON file, preserving topic assignments.
*   **Responsive Design**: Optimized for both desktop and mobile usage with touch swipe gestures.
*   **Persistent Storage**: Uses a local SQLite database to save your data.

## Tech Stack

*   **Backend**: Python, Flask, SQLAlchemy, SQLite
*   **Frontend**: React (via CDN), Tailwind CSS, Sortable.js (for drag-and-drop)
*   **Security**: Werkzeug (Password Hashing), Flask-Login (Session Management)

## Installation

1.  **Clone the repository** (or download the source code):
    ```bash
    git clone <repository-url>
    cd flashcards-study-tool
    ```

2.  **Install Dependencies**:
    Make sure you have Python installed, then run:
    ```bash
    pip install -r requirements.txt
    ```

3.  **Configuration**:
    Create a `.env` file in the root directory to store your secret key securely.
    ```bash
    # .env
    SECRET_KEY=your-super-secret-random-key
    ```

## Usage

1.  **Start the Server**:
    ```bash
    python app.py
    ```

2.  **Access the Application**:
    *   Open your web browser and go to: `http://localhost:5000`
    *   To access from another device on your Wi-Fi, find your computer's IP address (e.g., `192.168.1.X`) and visit `http://192.168.1.X:5000`.

3.  **Get Started**:
    *   Register a new account.
    *   Click "Add Card" to create your first flashcard.
    *   Or, click "Import JSON" to upload a batch of cards.

## Importing Cards (JSON Format)

You can bulk import cards by uploading a `.json` file. The file should contain a list of objects with `topic`, `front`, and `back` keys. If the topic doesn't exist, it will be automatically created.

**Example `cards.json`:**
```json
[
  {
    "topic": "Mathematics",
    "category": "Basic Stuff",
    "front": "What is 2 + 2?",
    "back": "4"
  },
  {
    "topic": "History",
    "front": "Who was the first President of the USA?",
    "back": "George Washington"
  }
]
```

## License

[MIT](https://choosealicense.com/licenses/mit/)
