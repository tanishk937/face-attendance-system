"""
SmartFace Attendance - Prototype Backend
=========================================
FastAPI backend that reuses the core logic of the original Tkinter app
(face encoding storage, face_distance matching, once-per-day dedupe)
but exposes it as a REST API so a browser (desktop OR mobile) can drive it
via getUserMedia instead of cv2.imshow().

Run with:  uvicorn main:app --reload
"""

import base64
import io
import pickle
import sqlite3
import datetime
import logging
from pathlib import Path
from typing import List, Optional

import numpy as np
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from PIL import Image

from fastapi.responses import FileResponse
from pathlib import Path

import face_recognition

# ---------------------------------------------------------------------------
# Config (env-var friendly stubs — swap in real env loading when you extend)
# ---------------------------------------------------------------------------
DB_PATH = Path(__file__).parent / "smartface.db"
RECOGNITION_THRESHOLD = 0.5  # lower face_distance = stricter match. Tune this.
ATTENDANCE_MODE = "once_per_day"  # or "check_in_out" later

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("smartface")

app = FastAPI(title="SmartFace Attendance (Prototype)")

BASE_DIR = Path(__file__).resolve().parent

@app.get("/")
async def serve_frontend():
    return FileResponse(BASE_DIR / "index.html")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten this before any real deployment
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            department TEXT DEFAULT '',
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS face_encodings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            encoding TEXT NOT NULL,
            sample_count INTEGER NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            time TEXT NOT NULL,
            match_score REAL,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            UNIQUE(user_id, date)  -- enforces once-per-day at the DB level
        );
        """
    )
    conn.commit()
    conn.close()


init_db()

# ---------------------------------------------------------------------------
# Face encoding helpers (same idea as your original encode/decode functions)
# ---------------------------------------------------------------------------
def encoding_to_str(encoding: np.ndarray) -> str:
    return base64.b64encode(pickle.dumps(encoding)).decode("utf-8")


def str_to_encoding(s: str) -> np.ndarray:
    return pickle.loads(base64.b64decode(s))


def decode_image(image_b64: str) -> np.ndarray:
    """Accepts a data URL or raw base64 JPEG/PNG and returns an RGB numpy array."""
    if "," in image_b64:
        image_b64 = image_b64.split(",", 1)[1]
    img_bytes = base64.b64decode(image_b64)
    img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
    return np.array(img)


def load_known_faces():
    conn = get_conn()
    rows = conn.execute(
        """
        SELECT u.id as user_id, u.name, u.department, f.encoding
        FROM users u JOIN face_encodings f ON f.user_id = u.id
        """
    ).fetchall()
    conn.close()
    ids, names, depts, encodings = [], [], [], []
    for r in rows:
        try:
            encodings.append(str_to_encoding(r["encoding"]))
            ids.append(r["user_id"])
            names.append(r["name"])
            depts.append(r["department"])
        except Exception:
            log.warning("Corrupted encoding for user_id=%s, skipping", r["user_id"])
    return ids, names, depts, encodings


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------
class RegisterRequest(BaseModel):
    name: str
    department: Optional[str] = ""
    images: List[str]  # list of base64 data URLs, ideally 3-5 samples


class RecognizeRequest(BaseModel):
    image: str


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.get("/api/health")
def health():
    return {
        "status": "online",
        "database": "connected",
        "face_engine": "ready",
        "recognition_threshold": RECOGNITION_THRESHOLD,
    }


@app.post("/api/users")
def register_user(req: RegisterRequest):
    if not req.name.strip():
        raise HTTPException(400, "Name cannot be empty")
    if not req.images:
        raise HTTPException(400, "At least one face sample is required")

    sample_encodings = []
    for i, img_b64 in enumerate(req.images):
        try:
            rgb = decode_image(img_b64)
        except Exception:
            continue
        locations = face_recognition.face_locations(rgb)
        if len(locations) != 1:
            log.info("Sample %d skipped: found %d faces", i, len(locations))
            continue
        enc = face_recognition.face_encodings(rgb, locations)[0]
        sample_encodings.append(enc)

    if not sample_encodings:
        raise HTTPException(
            422, "No usable face samples (need exactly one clear face per frame)"
        )

    # Average multiple samples into one robust representation
    final_encoding = np.mean(sample_encodings, axis=0)

    conn = get_conn()
    cur = conn.execute(
        "INSERT INTO users (name, department, created_at) VALUES (?, ?, ?)",
        (req.name.strip(), req.department or "", datetime.datetime.now().isoformat()),
    )
    user_id = cur.lastrowid
    conn.execute(
        "INSERT INTO face_encodings (user_id, encoding, sample_count) VALUES (?, ?, ?)",
        (user_id, encoding_to_str(final_encoding), len(sample_encodings)),
    )
    conn.commit()
    conn.close()

    log.info("Registered user_id=%s name=%s samples=%d", user_id, req.name, len(sample_encodings))
    return {
        "user_id": user_id,
        "name": req.name,
        "samples_used": len(sample_encodings),
        "samples_submitted": len(req.images),
    }


@app.get("/api/users")
def list_users():
    conn = get_conn()
    rows = conn.execute(
        """
        SELECT u.id, u.name, u.department, u.created_at,
               (SELECT MAX(date || ' ' || time) FROM attendance a WHERE a.user_id = u.id) as last_attendance
        FROM users u ORDER BY u.created_at DESC
        """
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@app.delete("/api/users/{user_id}")
def delete_user(user_id: int):
    conn = get_conn()
    conn.execute("PRAGMA foreign_keys = ON")
    cur = conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()
    if cur.rowcount == 0:
        raise HTTPException(404, "User not found")
    return {"deleted": user_id}


@app.post("/api/attendance/recognize")
def recognize(req: RecognizeRequest):
    ids, names, depts, encodings = load_known_faces()

    try:
        rgb = decode_image(req.image)
    except Exception:
        raise HTTPException(400, "Invalid image data")

    locations = face_recognition.face_locations(rgb)

    if len(locations) == 0:
        return {"status": "no_face"}
    if len(locations) > 1:
        return {"status": "multiple_faces", "count": len(locations)}

    if not encodings:
        return {"status": "unknown", "reason": "no_registered_users"}

    face_encoding = face_recognition.face_encodings(rgb, locations)[0]
    distances = face_recognition.face_distance(encodings, face_encoding)
    best_idx = int(np.argmin(distances))
    best_distance = float(distances[best_idx])

    if best_distance > RECOGNITION_THRESHOLD:
        return {"status": "unknown", "match_score": round(1 - best_distance, 3)}

    user_id = ids[best_idx]
    name = names[best_idx]
    department = depts[best_idx]
    now = datetime.datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H:%M:%S")

    conn = get_conn()
    already = conn.execute(
        "SELECT 1 FROM attendance WHERE user_id = ? AND date = ?", (user_id, date_str)
    ).fetchone()

    if already:
        conn.close()
        return {
            "status": "already_marked",
            "name": name,
            "department": department,
            "match_score": round(1 - best_distance, 3),
        }

    conn.execute(
        "INSERT INTO attendance (user_id, date, time, match_score) VALUES (?, ?, ?, ?)",
        (user_id, date_str, time_str, round(1 - best_distance, 3)),
    )
    conn.commit()
    conn.close()

    log.info("Attendance marked: %s at %s (score=%.3f)", name, time_str, 1 - best_distance)
    return {
        "status": "marked",
        "name": name,
        "department": department,
        "time": time_str,
        "date": date_str,
        "match_score": round(1 - best_distance, 3),
    }


@app.get("/api/attendance")
def list_attendance(date: Optional[str] = None):
    conn = get_conn()
    query = """
        SELECT a.id, u.name, u.department, a.date, a.time, a.match_score
        FROM attendance a JOIN users u ON u.id = a.user_id
    """
    params = ()
    if date:
        query += " WHERE a.date = ?"
        params = (date,)
    query += " ORDER BY a.date DESC, a.time DESC"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@app.get("/api/dashboard/summary")
def dashboard_summary():
    conn = get_conn()
    total_users = conn.execute("SELECT COUNT(*) c FROM users").fetchone()["c"]
    today = datetime.date.today().isoformat()
    present_today = conn.execute(
        "SELECT COUNT(*) c FROM attendance WHERE date = ?", (today,)
    ).fetchone()["c"]
    conn.close()
    return {
        "total_users": total_users,
        "present_today": present_today,
        "absent_today": max(total_users - present_today, 0),
        "date": today,
    }


# Serve the frontend (single-page prototype) from the same origin so you
# don't have to deal with CORS during local dev.
FRONTEND_DIR = Path(__file__).parent / "frontend"
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

    @app.get("/")
    def index():
        return FileResponse(str(FRONTEND_DIR / "index.html"))
