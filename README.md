# Face Attendance Project

A browser-based face recognition attendance system built with **FastAPI, OpenCV, face_recognition, SQLite, HTML, CSS, and JavaScript**.

This prototype converts a traditional Tkinter/MySQL face-recognition attendance system into a web-based application. The camera and user interface run directly in the browser, allowing the system to work with both **laptop webcams and phone cameras** without requiring a separate mobile application.

The prototype focuses on proving the complete workflow:

**Register Face → Recognize Face → Mark Attendance → View Dashboard**

---

## Features

* 📷 Browser-based camera using `getUserMedia`
* 👤 Face registration with multiple samples
* 🧠 Face recognition using `face_recognition`
* 📊 Face matching using `face_distance`
* 🎯 Configurable recognition threshold
* 📝 Automatic attendance marking
* 🔒 Once-per-day attendance protection
* 🗄️ SQLite database with automatic initialization
* 📈 Attendance dashboard
* 👥 Registered user management
* 🗑️ User deletion
* 🌐 REST API using FastAPI
* 💻 Works with laptop/desktop webcams
* 📱 Can be tested using a phone camera
* ⚡ No frontend build system required

---

## System Workflow

```text
                    ┌─────────────────────┐
                    │   Browser Camera    │
                    │  Laptop / Mobile    │
                    └──────────┬──────────┘
                               │
                               │ Image Frame
                               ▼
                    ┌─────────────────────┐
                    │     FastAPI API     │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │ Face Detection &    │
                    │ Face Encoding       │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │ Face Distance       │
                    │ Comparison          │
                    └──────────┬──────────┘
                               │
                       Match Found?
                         /         \
                       Yes          No
                        │            │
                        ▼            ▼
               ┌──────────────┐   Unknown
               │ Mark         │
               │ Attendance   │
               └──────┬───────┘
                      │
                      ▼
               ┌──────────────┐
               │   SQLite DB  │
               └──────┬───────┘
                      │
                      ▼
               ┌──────────────┐
               │  Dashboard   │
               └──────────────┘
```

---

## Project Structure

```text
smartface-prototype/
│
├── main.py
├── requirements.txt
├── smartface.db
│
└── frontend/
    └── index.html
```

### Main Components

| File                  | Description                                                          |
| --------------------- | -------------------------------------------------------------------- |
| `main.py`             | FastAPI backend, face recognition, database operations and REST APIs |
| `frontend/index.html` | Browser-based user interface                                         |
| `requirements.txt`    | Python dependencies                                                  |
| `smartface.db`        | SQLite database created automatically                                |

---

## Technology Stack

### Backend

* Python
* FastAPI
* Uvicorn
* OpenCV
* face_recognition
* NumPy
* SQLite

### Frontend

* HTML5
* CSS3
* JavaScript
* Browser MediaDevices API (`getUserMedia`)

### Database

* SQLite

---

## Requirements

Recommended environment:

* Python 3.10 / 3.11
* Webcam
* Modern web browser
* CMake
* C++ compiler

`face_recognition` depends on **dlib**, which may require additional build tools during installation.

---

# Installation

## 1. Clone the Repository

```bash
git clone <YOUR_GITHUB_REPOSITORY_URL>
cd smartface-prototype
```

---

## 2. Create Virtual Environment

### Linux / macOS

```bash
python3 -m venv venv
source venv/bin/activate
```

### Windows

```bash
python -m venv venv
venv\Scripts\activate
```

---

## 3. Install Dependencies

```bash
pip install -r requirements.txt
```

If `dlib` installation fails, install the required build tools first.

### Ubuntu / Debian

```bash
sudo apt update
sudo apt install cmake build-essential
```

Then:

```bash
pip install -r requirements.txt
```

### macOS

```bash
brew install cmake
```

Then:

```bash
pip install -r requirements.txt
```

---

# Run the Application

Start the FastAPI server:

```bash
uvicorn main:app --reload
```

Open the application in your browser:

```text
http://localhost:8000
```

Grant camera permission when requested.

---

# Using the Application

## 1. Register a User

Open the **Register User** tab.

Enter:

* Name
* Department

Then capture approximately **3–5 face samples**.

Try to capture samples with:

* Slightly different angles
* Different facial expressions
* Normal lighting conditions

The backend generates face encodings for the samples and averages them into a representative encoding for the user.

---

## 2. Mark Attendance

Open the **Mark Attendance** tab.

Click:

```text
Start Scanning
```

The browser captures camera frames and periodically sends them to:

```text
/api/attendance/recognize
```

The backend:

1. Detects faces.
2. Generates a face encoding.
3. Compares it with registered users.
4. Calculates face distance.
5. Applies the recognition threshold.
6. Identifies the user if a valid match is found.
7. Marks attendance.

---

## 3. Once-Per-Day Attendance

A user can only receive one attendance record per day.

The database enforces this using:

```sql
UNIQUE(user_id, date)
```

Therefore, if the same person is recognized again on the same day, the system reports:

```text
Already marked
```

instead of creating another attendance record.

---

## 4. Dashboard

The **Dashboard** provides:

* Total registered users
* Today's attendance count
* Recent attendance records
* Registered users
* User deletion

---

# Face Recognition

The system uses the `face_recognition` library and compares face encodings using:

```python
face_distance()
```

The main recognition parameter is:

```python
RECOGNITION_THRESHOLD = 0.5
```

The system checks whether the calculated face distance is within the configured threshold.

### Threshold Behavior

```text
Lower threshold
      ↓
Stricter matching
      ↓
Fewer false matches
      ↓
Higher chance of rejecting valid users
```

```text
Higher threshold
      ↓
More relaxed matching
      ↓
Easier recognition
      ↓
Higher chance of false matches
```

The default value should be treated as a starting point and tuned using real test data.

---

# Similarity Score

The prototype converts face distance into a simple normalized similarity value:

```text
similarity = 1 - face_distance
```

This value is intended as a **similarity score**, not a calibrated probability.

For example:

```text
Lower face distance → Better match
Higher face distance → Worse match
```

---

# API Endpoints

The FastAPI backend exposes REST endpoints for:

### User Registration

```text
/api/users
```

Used to register users and their face encodings.

### Face Recognition / Attendance

```text
/api/attendance/recognize
```

Receives a camera frame, performs recognition and handles attendance marking.

### Attendance Records

```text
/api/attendance
```

Used to retrieve attendance information.

### Dashboard

```text
/api/dashboard
```

Provides dashboard statistics and recent activity.

### Users

```text
/api/users
```

Provides registered user information and management operations.

The exact request and response schemas can be inspected through FastAPI's automatically generated API documentation.

Open:

```text
http://localhost:8000/docs
```

---

# Testing With a Phone Camera

The application can also be tested using a phone camera.

Start the server on your local network:

```bash
uvicorn main:app --host 0.0.0.0 --reload
```

Find your computer's local IP address.

For example:

```text
192.168.1.23
```

Then open this address on your phone:

```text
http://192.168.1.23:8000
```

Make sure:

* Phone and computer are connected to the same Wi-Fi.
* Port `8000` is accessible.
* Browser camera permission is enabled.

### Important

Most mobile browsers require a **secure context (`HTTPS`)** for camera access.

For reliable phone testing, use an HTTPS tunnel such as `ngrok` or deploy the application behind a reverse proxy with TLS.

---

# Database

The prototype uses SQLite so that no separate database server is required.

The database file:

```text
smartface.db
```

is automatically created when the application starts.

The database stores information such as:

* Registered users
* Face encodings
* Departments
* Attendance records
* Attendance dates

SQLite makes the prototype easy to run and test without additional database configuration.

---

# Configuration

The main configuration values are located in:

```text
main.py
```

## Recognition Threshold

```python
RECOGNITION_THRESHOLD = 0.5
```

Lower values provide stricter recognition.

---

## Database Path

The SQLite database location can also be configured using:

```python
DB_PATH
```

This can be changed if the database needs to be stored somewhere else.

---

# Security Considerations

This project is currently a **prototype**.

The current version does not include authentication or authorization.

Therefore:

> Do not expose the application directly to the public internet in its current form.

Before production deployment, implement:

* User authentication
* Admin authorization
* Password hashing
* HTTPS
* Secure session/JWT handling
* Environment variables for secrets
* Input validation
* Rate limiting
* Audit logging
* Secure database configuration

---

# Known Limitations

### 1. No Authentication

All API endpoints are currently accessible without login.

---

### 2. No Anti-Spoofing

The prototype uses single-frame face recognition.

A photograph or screen showing a registered person's face may potentially pass recognition.

Production systems should consider:

* Liveness detection
* Blink detection
* Head movement
* Depth sensing
* IR cameras
* Dedicated anti-spoofing models

---

### 3. dlib Installation

`face_recognition` depends on dlib, which can be difficult to install on some systems.

CMake and a C++ compiler may be required.

---

### 4. Recognition Threshold

The default threshold:

```text
0.5
```

is not universally optimal.

Real-world performance depends on:

* Camera quality
* Lighting
* Face angle
* Distance from camera
* Image resolution
* Registration quality

The threshold should be evaluated using actual genuine and non-genuine face samples.

---

### 5. SQLite

SQLite is suitable for this prototype but may not be the best choice for a large multi-user deployment.

For production, consider:

* PostgreSQL
* MySQL

---

# What I Would Extend Next

The prototype can be developed into a more complete attendance platform.

### 1. Production Database

Replace:

```text
SQLite
```

with:

```text
PostgreSQL / MySQL
```

---

### 2. Authentication

Add:

* Admin login
* User roles
* Password hashing
* JWT/session authentication
* Protected API endpoints

---

### 3. Environment Configuration

Move configuration and secrets into environment variables.

Example:

```text
.env
```

Use:

```text
.env.example
```

for safe configuration documentation.

Never commit real secrets to GitHub.

---

### 4. Check-In / Check-Out

Extend attendance from:

```text
Once per day
```

to:

```text
Check In
    ↓
Working
    ↓
Check Out
```

---

### 5. Reports

Add:

* CSV export
* Excel reports
* PDF reports
* Date filtering
* Department filtering
* Monthly attendance reports

---

### 6. HTTPS Deployment

Deploy the application using:

```text
Nginx
+
HTTPS/TLS
+
FastAPI
```

or another production-ready deployment architecture.

---

### 7. PWA

Convert the frontend into a Progressive Web App using:

```text
manifest.json
service-worker.js
```

This can provide a more app-like experience without building a separate native mobile application.

---

### 8. Audit Logging

Add an audit log for important administrative actions such as:

```text
User registered
User deleted
Attendance modified
Threshold changed
Admin login
```

---

### 9. Department Management

Instead of storing departments as free text, create dedicated department records and relationships.

Example:

```text
Departments
     │
     ├── Robotics
     ├── Computer Science
     ├── Mechanical
     └── Electrical
```

---

# Prototype Status

**Status: Working Prototype**

The core end-to-end flow has been implemented:

```text
Browser Camera
      ↓
Face Registration
      ↓
Face Encoding
      ↓
Face Recognition
      ↓
Face Matching
      ↓
Attendance Marking
      ↓
SQLite Database
      ↓
Dashboard
```

The project is intentionally focused on validating the core functionality before adding production-level features.

---

# Future Architecture

A possible production architecture:

```text
                 Web / Mobile Browser
                         │
                         ▼
                  HTTPS / Reverse Proxy
                         │
                         ▼
                     FastAPI
                         │
             ┌───────────┴───────────┐
             │                       │
             ▼                       ▼
      Face Recognition          Authentication
             │                       │
             └───────────┬───────────┘
                         │
                         ▼
                   PostgreSQL
                         │
              ┌──────────┴──────────┐
              │                     │
              ▼                     ▼
          Attendance             Audit Logs
              │
              ▼
           Reports
```

---

# License

This project is intended as a prototype and learning project.

Add an appropriate license before distributing or deploying it publicly.

---

# Author

**Tanishk Patidar**

Robotics & Automation Engineer | Robotics Software | Computer Vision | AI

---

## Disclaimer

This project is a prototype intended for development, experimentation, and demonstration purposes.

It should not be considered a production-ready biometric attendance or access-control system without implementing appropriate security, privacy, authentication, liveness detection, data protection, and compliance measures.
