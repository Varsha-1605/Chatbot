# AI Chatbot 🤖

An intelligent, full-featured conversational AI designed to provide dynamic and context-aware responses. Built with **Python** and **Flask**, this project integrates a robust AI model with a user-friendly web interface, offering capabilities like sentiment analysis, document-based querying, and a full-fledged administrative dashboard.

-----

## Project Demo:

### 1. User Side:

https://github.com/user-attachments/assets/58b52af5-9769-4901-8e36-cd5bbc8db6e6

### 2. Admin Side:

https://github.com/user-attachments/assets/9b3d0c6f-d22f-425d-9290-0309c03e959a


## 🌟 Features

  * **Conversational Core**: The chatbot brain (`chatbot_brain.py`) uses a powerful AI model to process natural language queries and generate human-like responses.
  * **User Management**: Secure user registration, login, and profile management are handled with **Flask-Login** and a **SQLite** database.
  * **Dynamic Knowledge Base**: Users and admins can upload documents (`.txt`, `.pdf`, etc.) to extend the chatbot's knowledge base in real-time. The `document_processor.py` module handles parsing and preparing these documents for the AI.
  * **Sentiment Analysis**: The `sentiment_analyzer.py` module analyzes user input to determine the emotional tone, providing valuable insights into user satisfaction.
  * **Interactive UI**: A modern, responsive web interface is built with **HTML**, **CSS** (using **Tailwind CSS** for utility-first styling), and **JavaScript** for a seamless chat experience. It includes features like:
      * **Animated Typing Indicator**: Visual feedback while the AI is processing a response.
      * **Code and Markdown Formatting**: The chatbot's responses are beautifully formatted with support for code blocks, bold text, lists, and more.
      * **Chat History and Export**: Users can view their past conversations and download their chat history.
  * **Admin & Analytics Dashboard**: A dedicated admin panel provides powerful tools for monitoring and managing the chatbot system, including:
      * Real-time analytics on conversations, users, and sentiment distribution.
      * System status monitoring.
      * Tools to manage users, conversations, and system settings.
  * **Robust Error Handling**: The application includes custom error pages for common issues like `404 Not Found` and `500 Internal Server Error`, ensuring a professional user experience.

-----

## 🚀 Getting Started

### Prerequisites

You'll need **Python 3.x** and `pip` installed on your system.

### Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/Varsha-1605/Chatbot.git
    cd Chatbot
    ```
2.  **Create a virtual environment:**
    ```bash
    python -m venv myenv
    source myenv/bin/activate  # On Windows, use `myenv\Scripts\activate`
    ```
3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
4.  **Set up environment variables:**
    Create a `.env` file in the project root directory and add a secret key for session management.
    ```env
    SECRET_KEY='your-strong-and-random-secret-key'
    ```

### Running the Application

1.  **Start the Flask development server:**
    ```bash
    python app.py
    ```
2.  **Access the application:**
    Open your web browser and navigate to `http://127.0.0.1:5000`.

-----

## 📂 Project Structure

```
.
├── __pycache__/             # Python cache files
├── logs/                    # Directory for log files (e.g., chatbot.log)
├── myenv/                   # Python virtual environment
├── static/                  # Frontend assets
│   ├── css/
│   │   └── styles.css       # Custom CSS for styling and animations
│   ├── images/              # Placeholder for images
│   └── js/
│       └── chatbot.js       # Core JavaScript for chat functionality
├── templates/               # HTML templates using Jinja2
│   ├── auth/                # Authentication templates (login, register)
│   ├── errors/              # Error pages (404, 500)
│   ├── admin.html           # Admin dashboard panel
│   ├── analytics.html       # Analytics dashboard
│   ├── base.html            # Main template for consistent layout
│   ├── index.html           # Main chat page
│   ├── profile.html         # User profile page
│   └── user_history.html    # Page to view chat history
├── uploads/                 # Storage for uploaded documents
├── .env                     # Environment variables file
├── .gitignore               # Git ignore file
├── app.py                   # Main Flask application with routes and logic
├── chatbot_brain.py         # Handles core AI logic and interactions
├── config.py                # Application configuration settings
├── database.py              # Manages database connection and schema
├── document_processor.py    # Logic for processing and embedding documents
├── models.py                # Defines database models (User, Message, etc.)
├── requirements.txt         # List of Python dependencies
├── sentiment_analyzer.py    # Analyzes and scores message sentiment
└── test.py                  # Placeholder for project tests
```

-----

## 🤝 Contribution

Contributions are highly welcome\! If you'd like to improve this project, please follow these steps:

1.  Fork the repository.
2.  Create a new feature branch (`git checkout -b feature/amazing-feature`).
3.  Commit your changes (`git commit -m 'feat: add amazing feature'`).
4.  Push to the branch (`git push origin feature/amazing-feature`).
5.  Open a Pull Request.

-----

## 📄 License

This project is open-source and available under the **MIT License**.
