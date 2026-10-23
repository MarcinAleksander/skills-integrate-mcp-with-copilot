"""
High School Management System API

A super simple FastAPI application that allows students to view and sign up
for extracurricular activities at Mergington High School.
"""

import hashlib
import hmac
import json
import logging
import os
import secrets
import time
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, ValidationError

app = FastAPI(title="Mergington High School API",
              description="API for viewing and signing up for extracurricular activities")

# Mount the static files directory
current_dir = Path(__file__).parent
app.mount("/static", StaticFiles(directory=os.path.join(Path(__file__).parent,
          "static")), name="static")

logger = logging.getLogger(__name__)
TEACHERS_FILE = Path(os.getenv("TEACHERS_FILE", current_dir / "teachers.json"))
SESSION_COOKIE = "teacher_session"
SESSION_TTL_SECONDS = 8 * 60 * 60
PASSWORD_HASH_ITERATIONS = 310_000
COOKIE_SECURE = os.getenv("COOKIE_SECURE", "false").lower() in ("1", "true", "yes")
teacher_sessions: dict[str, tuple[str, float]] = {}


class TeacherLogin(BaseModel):
    username: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=1, max_length=1024)


class TeacherCredential(BaseModel):
    username: str = Field(min_length=1, max_length=100)
    salt: str = Field(min_length=32, max_length=128)
    password_hash: str = Field(min_length=64, max_length=64)


def load_teacher_credentials() -> list[TeacherCredential]:
    try:
        data = json.loads(TEACHERS_FILE.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        logger.error("Teacher credentials file is missing: %s", TEACHERS_FILE)
        raise HTTPException(
            status_code=503,
            detail="Teacher login is not configured",
        ) from error
    except json.JSONDecodeError as error:
        logger.exception("Teacher credentials file contains invalid JSON")
        raise HTTPException(
            status_code=500,
            detail="Teacher login is misconfigured",
        ) from error
    except OSError as error:
        logger.exception("Teacher credentials file could not be read")
        raise HTTPException(
            status_code=500,
            detail="Teacher login is misconfigured",
        ) from error

    if not isinstance(data, list):
        logger.error("Teacher credentials file must contain a JSON array")
        raise HTTPException(
            status_code=500,
            detail="Teacher login is misconfigured",
        )

    try:
        credentials = [TeacherCredential.model_validate(item) for item in data]
    except ValidationError as error:
        logger.exception("Teacher credentials file contains an invalid record")
        raise HTTPException(
            status_code=500,
            detail="Teacher login is misconfigured",
        ) from error

    if not credentials:
        raise HTTPException(
            status_code=503,
            detail="No teacher accounts are configured",
        )
    if len({credential.username for credential in credentials}) != len(credentials):
        logger.error("Teacher usernames must be unique")
        raise HTTPException(
            status_code=500,
            detail="Teacher login is misconfigured",
        )
    try:
        for credential in credentials:
            if len(bytes.fromhex(credential.salt)) < 16:
                raise ValueError("salt must contain at least 16 bytes")
            if len(bytes.fromhex(credential.password_hash)) != 32:
                raise ValueError("password hash must contain 32 bytes")
    except ValueError as error:
        logger.error("Teacher credentials contain an invalid salt or password hash")
        raise HTTPException(
            status_code=500,
            detail="Teacher login is misconfigured",
        ) from error
    return credentials


def password_digest(password: str, salt: bytes) -> str:
    return hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        PASSWORD_HASH_ITERATIONS,
    ).hex()


def authenticate_teacher(username: str, password: str) -> bool:
    credentials = load_teacher_credentials()
    stored_credential = next(
        (credential for credential in credentials if credential.username == username),
        None,
    )
    if stored_credential is None:
        password_digest(password, b"\0" * 16)
        return False

    salt = bytes.fromhex(stored_credential.salt)
    candidate = password_digest(password, salt)
    return hmac.compare_digest(candidate, stored_credential.password_hash)


def require_teacher(request: Request) -> str:
    token = request.cookies.get(SESSION_COOKIE)
    session = teacher_sessions.get(token or "")
    if session is None or session[1] <= time.time():
        if token:
            teacher_sessions.pop(token, None)
        raise HTTPException(status_code=401, detail="Teacher login required")
    return session[0]


# In-memory activity database
activities = {
    "Chess Club": {
        "description": "Learn strategies and compete in chess tournaments",
        "schedule": "Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 12,
        "participants": ["michael@mergington.edu", "daniel@mergington.edu"]
    },
    "Programming Class": {
        "description": "Learn programming fundamentals and build software projects",
        "schedule": "Tuesdays and Thursdays, 3:30 PM - 4:30 PM",
        "max_participants": 20,
        "participants": ["emma@mergington.edu", "sophia@mergington.edu"]
    },
    "Gym Class": {
        "description": "Physical education and sports activities",
        "schedule": "Mondays, Wednesdays, Fridays, 2:00 PM - 3:00 PM",
        "max_participants": 30,
        "participants": ["john@mergington.edu", "olivia@mergington.edu"]
    },
    "Soccer Team": {
        "description": "Join the school soccer team and compete in matches",
        "schedule": "Tuesdays and Thursdays, 4:00 PM - 5:30 PM",
        "max_participants": 22,
        "participants": ["liam@mergington.edu", "noah@mergington.edu"]
    },
    "Basketball Team": {
        "description": "Practice and play basketball with the school team",
        "schedule": "Wednesdays and Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["ava@mergington.edu", "mia@mergington.edu"]
    },
    "Art Club": {
        "description": "Explore your creativity through painting and drawing",
        "schedule": "Thursdays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["amelia@mergington.edu", "harper@mergington.edu"]
    },
    "Drama Club": {
        "description": "Act, direct, and produce plays and performances",
        "schedule": "Mondays and Wednesdays, 4:00 PM - 5:30 PM",
        "max_participants": 20,
        "participants": ["ella@mergington.edu", "scarlett@mergington.edu"]
    },
    "Math Club": {
        "description": "Solve challenging problems and participate in math competitions",
        "schedule": "Tuesdays, 3:30 PM - 4:30 PM",
        "max_participants": 10,
        "participants": ["james@mergington.edu", "benjamin@mergington.edu"]
    },
    "Debate Team": {
        "description": "Develop public speaking and argumentation skills",
        "schedule": "Fridays, 4:00 PM - 5:30 PM",
        "max_participants": 12,
        "participants": ["charlotte@mergington.edu", "henry@mergington.edu"]
    }
}


@app.get("/")
def root():
    return RedirectResponse(url="/static/index.html")


@app.get("/activities")
def get_activities():
    return activities


@app.post("/auth/session")
def create_teacher_session(login: TeacherLogin, response: Response):
    if not authenticate_teacher(login.username, login.password):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    token = secrets.token_urlsafe(32)
    teacher_sessions[token] = (login.username, time.time() + SESSION_TTL_SECONDS)
    response.set_cookie(
        key=SESSION_COOKIE,
        value=token,
        max_age=SESSION_TTL_SECONDS,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite="strict",
        path="/",
    )
    return {"username": login.username}


@app.get("/auth/session")
def get_teacher_session(username: str = Depends(require_teacher)):
    return {"username": username}


@app.delete("/auth/session")
def delete_teacher_session(request: Request, response: Response):
    token = request.cookies.get(SESSION_COOKIE)
    if token:
        teacher_sessions.pop(token, None)
    response.delete_cookie(
        key=SESSION_COOKIE,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite="strict",
        path="/",
    )
    return {"message": "Signed out"}


@app.post("/activities/{activity_name}/signup")
def signup_for_activity(
    activity_name: str,
    email: str,
    _: str = Depends(require_teacher),
):
    """Register a student for an activity (teachers only)."""
    # Validate activity exists
    if activity_name not in activities:
        raise HTTPException(status_code=404, detail="Activity not found")

    # Get the specific activity
    activity = activities[activity_name]

    # Validate student is not already signed up
    if email in activity["participants"]:
        raise HTTPException(
            status_code=400,
            detail="Student is already signed up"
        )

    # Add student
    activity["participants"].append(email)
    return {"message": f"Signed up {email} for {activity_name}"}


@app.delete("/activities/{activity_name}/unregister")
def unregister_from_activity(
    activity_name: str,
    email: str,
    _: str = Depends(require_teacher),
):
    """Unregister a student from an activity (teachers only)."""
    # Validate activity exists
    if activity_name not in activities:
        raise HTTPException(status_code=404, detail="Activity not found")

    # Get the specific activity
    activity = activities[activity_name]

    # Validate student is signed up
    if email not in activity["participants"]:
        raise HTTPException(
            status_code=400,
            detail="Student is not signed up for this activity"
        )

    # Remove student
    activity["participants"].remove(email)
    return {"message": f"Unregistered {email} from {activity_name}"}
