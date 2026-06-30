# Writing Authenticity Tracker

A machine learning-powered web application that analyzes written text and predicts whether it is human-written or AI-generated. The project combines natural language processing techniques with an interactive web interface to provide quick and accurate authenticity analysis.

---

## Overview

The Writing Authenticity Tracker helps users determine whether a piece of text is likely to have been written by a human or generated using artificial intelligence. It leverages machine learning techniques for text classification and provides results through a simple web interface.

---

## Features

* Detects whether text is AI-generated or human-written
* Clean and user-friendly web interface
* Fast prediction using a trained machine learning model
* Real-time text analysis
* Lightweight and easy to deploy

---

## Tech Stack

### Frontend

* HTML
* CSS
* JavaScript

### Backend

* Python
* Flask

### Machine Learning

* Scikit-learn
* Pandas
* NumPy
* Joblib

---

## Project Structure

```text
Writing-Authenticity-Tracker/
│
├── static/              # CSS, JavaScript, images
├── templates/           # HTML templates
├── model/               # Trained ML model
├── app.py               # Flask application
├── requirements.txt     # Python dependencies
├── README.md
└── ...
```

---

## Installation

### Clone the repository

```bash
git clone https://github.com/AKARSH24012006/Writing-Authenticity-Tracker.git
```

### Navigate to the project directory

```bash
cd Writing-Authenticity-Tracker
```

### Create a virtual environment (Optional)

**Windows**

```bash
python -m venv venv
venv\Scripts\activate
```

**Linux/macOS**

```bash
python3 -m venv venv
source venv/bin/activate
```

### Install dependencies

```bash
pip install -r requirements.txt
```

### Run the application

```bash
python app.py
```

Open your browser and visit:

```text
http://127.0.0.1:5000
```

---

## Screenshots

You can add screenshots of the application here.

Example:

```text
screenshots/
├── home.png
├── prediction.png
└── result.png
```

---

## Future Improvements

* Deep learning-based classification
* Confidence score visualization
* Support for multiple languages
* User authentication
* REST API for external integrations
* Explainable AI insights

---

## Contributing

Contributions are welcome.

1. Fork the repository.
2. Create a new feature branch.
3. Commit your changes.
4. Push the branch.
5. Open a Pull Request.

---

## License

This project is intended for educational and research purposes. Feel free to modify and extend it for your own learning.

---

## Author

**Akarsh Nehra**

GitHub: https://github.com/AKARSH24012006

If you found this project useful, consider starring the repository.
