# Mergington High School Activities API

A super simple FastAPI application that allows students to view and sign up for extracurricular activities.

## Features

- View all available extracurricular activities
- Teachers can sign students up for and unregister students from activities

## Getting Started

1. Install the dependencies:

   ```
   pip install fastapi uvicorn
   ```

2. Configure teacher accounts before signing in. Copy `teachers.example.json` to
   `teachers.json`, then add a JSON array of accounts containing a username, a
   random salt (at least 16 bytes, in hexadecimal), and a PBKDF2-HMAC-SHA256
   password hash (310,000 iterations, in hexadecimal). Keep `teachers.json`
   private; it is ignored by Git. You can specify another path with the
   `TEACHERS_FILE` environment variable.

   Generate a salt and hash with Python:

   ```python
   import getpass
   import hashlib
   import json
   import secrets

   password = getpass.getpass("Teacher password: ")
   salt = secrets.token_bytes(16)
   password_hash = hashlib.pbkdf2_hmac(
       "sha256", password.encode(), salt, 310_000
   ).hex()
   print(json.dumps(
       [{
           "username": "teacher",
           "salt": salt.hex(),
           "password_hash": password_hash,
       }],
       indent=2,
   ))
   ```

   Save the printed JSON in `teachers.json`. Teacher sessions expire after
   eight hours or when the server restarts. Set `COOKIE_SECURE=true` when
   serving the site over HTTPS.

3. Run the app from the `src` directory:

   ```
   uvicorn app:app --reload
   ```

4. Open your browser and go to:
   - API documentation: http://localhost:8000/docs
   - Alternative documentation: http://localhost:8000/redoc
   - Activities website: http://localhost:8000/

## API Endpoints

| Method | Endpoint                                                          | Description                                                         |
| ------ | ----------------------------------------------------------------- | ------------------------------------------------------------------- |
| GET    | `/activities`                                                     | Public: view all activities and participants                         |
| POST   | `/auth/session`                                                   | Sign in as a teacher; sets an HTTP-only session cookie                |
| GET    | `/auth/session`                                                   | Get the current teacher session                                      |
| DELETE | `/auth/session`                                                   | Sign out                                                             |
| POST   | `/activities/{activity_name}/signup?email=student@mergington.edu` | Teacher-only: sign up a student                                      |
| DELETE | `/activities/{activity_name}/unregister?email=student@mergington.edu` | Teacher-only: unregister a student                                |

## Data Model

The application uses a simple data model with meaningful identifiers:

1. **Activities** - Uses activity name as identifier:

   - Description
   - Schedule
   - Maximum number of participants allowed
   - List of student emails who are signed up

2. **Students** - Uses email as identifier:
   - Name
   - Grade level

Activity and session data are stored in memory and reset when the server
restarts. Teacher password hashes are stored in the local `teachers.json` file.
