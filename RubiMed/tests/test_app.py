"""Integration tests for the core workflow; CI supplies a disposable MySQL service."""

import os
from uuid import uuid4

os.environ.setdefault("DB_HOST", "127.0.0.1")
os.environ.setdefault("DB_PORT", "3306")
os.environ.setdefault("DB_USER", "root")
os.environ.setdefault("DB_PASSWORD", "ci-password")
os.environ.setdefault("DB_NAME", "EHR_System")
os.environ.setdefault("SECRET_KEY", "test-session-secret")
os.environ.setdefault("RESET_TOKEN_SECRET", "test-reset-secret")

from app import app, db, generate_reset_token, confirm_reset_token  # noqa: E402
from werkzeug.security import generate_password_hash  # noqa: E402


app.config.update(TESTING=True)


def register_and_login(client):
    email = f"{uuid4().hex}@example.test"
    password = "test-only-password"
    response = client.post(
        "/register",
        data={"username": "Test Doctor", "email": email, "password": password},
        follow_redirects=True,
    )
    assert response.status_code == 200
    response = client.post(
        "/login", data={"email": email, "password": password}, follow_redirects=True
    )
    assert response.status_code == 200
    return email


def test_home_page_is_available():
    with app.test_client() as client:
        response = client.get("/")
    assert response.status_code == 200


def test_dashboard_requires_login():
    with app.test_client() as client:
        response = client.get("/dashboard")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_doctor_can_register_login_and_open_dashboard():
    with app.test_client() as client:
        register_and_login(client)
        response = client.get("/dashboard")
    assert response.status_code == 200


def test_doctor_cannot_open_another_doctors_patient():
    owner_email = f"{uuid4().hex}@example.test"
    other_email = f"{uuid4().hex}@example.test"
    cursor = db.cursor()
    cursor.execute(
        "INSERT INTO doctors (username, password, email) VALUES (%s, %s, %s)",
        ("Owner", generate_password_hash("owner-password"), owner_email),
    )
    owner_id = cursor.lastrowid
    cursor.execute(
        "INSERT INTO patients (doctor_id, first_name, last_name) VALUES (%s, %s, %s)",
        (owner_id, "Synthetic", "Patient"),
    )
    patient_id = cursor.lastrowid
    cursor.execute(
        "INSERT INTO doctors (username, password, email) VALUES (%s, %s, %s)",
        ("Other", generate_password_hash("other-password"), other_email),
    )
    db.commit()
    cursor.close()

    with app.test_client() as client:
        client.post("/login", data={"email": other_email, "password": "other-password"})
        response = client.get(f"/edit_patient/{patient_id}")
    assert response.status_code == 404


def test_password_reset_token_round_trip():
    email = f"{uuid4().hex}@example.test"
    assert confirm_reset_token(generate_reset_token(email)) == email
