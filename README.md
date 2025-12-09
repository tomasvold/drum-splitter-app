# 🥁 AI Drum Splitter App

A full-stack Python web application that uses the Music.AI API to separate stereo drum recordings into individual stems (kick, snare, hi-hat, toms, cymbals). This project showcases front-end asynchronous JavaScript and secure back-end API integration using Flask and environment variables.

---

## 🚀 Release
**Live Application:** https://drum-splitter-app.onrender.com/

## ✨ Features

* **Drum Stem Separation:**
    * Accepts stereo audio files containing drum recordings.
    * Utilizes the **Music.AI SDK** to process the audio using state-of-the-art AI.
    * Generates individual stems for **Kick, Snare, Toms, Cymbals, and Hi-hat**.
* **Asynchronous Job Processing:**
    * Manages the long-running audio processing job asynchronously.
    * The front-end uses **JavaScript Polling** to check the job status every 5 seconds without blocking the user interface.
* **Secure API Handling:**
    * Integrates the **Music.AI API** securely.
    * API keys are required from the user via the front-end form, ensuring **no secrets are stored publicly or hardcoded**.
    * Supports reading fallback API keys from environment variables (`os.environ`).
* **Robust Error Handling:**
    * Implements comprehensive `try/except/finally` blocks in Python to handle upload failures, API errors, and job processing failures.
    * Cleans up temporary uploaded files after processing attempts.

---

## 🛠️ Tech Stack & Tools

* **Backend Framework:** Python (Flask)
* **API Integration:** `musicai_sdk`
* **Environment Management:** `python-dotenv` and **OS Environment Variables** (for secure credential handling)
* **Asynchronous Processing:** Client-side **JavaScript polling** and **Fetch API**
* **Build/Deployment:** Render (using `Procfile`), `pip`/`requirements.txt`
* **Front-end:** HTML, CSS, Jinja Templating
* **Security:** Uses `werkzeug.utils.secure_filename` to prevent path traversal attacks.

---

## 📂 Project Structure

The application is structured to clearly separate back-end logic, front-end presentation, and static assets:

* `app.py`: The main Flask application file containing all API routes (`/`, `/upload`, `/job_status/<job_id>`) and job processing logic.
* `templates/`: Contains the HTML template files (e.g., `index.html`, `result.html`).
* `static/`: Stores static assets like CSS (`style.css`) and images (`Logo.png`).
* `requirements.txt`: Defines all Python dependencies required for the project.

---

## 💾 Installation and Local Run

To run this application locally:

1.  **Clone the repository:**
    ```bash
    git clone [https://github.com/tomasvold/drum-splitter-app.git](https://github.com/tomasvold/drum-splitter-app.git)
    cd drum-splitter-app
    ```
2.  **Set up the environment:**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows use `venv\Scripts\activate`
    pip install -r requirements.txt
    ```
3.  **Create a `.env` file** in the root directory and add your application-level API key (if needed):
    ```.env
    # Optional: If you want to use a fallback key for testing
    MUSIC_AI_APP_API_KEY="your_optional_music_ai_key" 
    FLASK_DEBUG=True
    ```
4.  **Run the application:**
    ```bash
    flask run
    ```
    The app will typically be available at `http://127.0.0.1:5000/`.

---

## 👤 Author

* **GitHub:** [tomasvold](https://github.com/tomasvold)
