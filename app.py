"""Flask application for student performance prediction and record management."""

from datetime import datetime
from contextlib import contextmanager
import os
from pathlib import Path
import sqlite3

import joblib
import pandas as pd
from flask import Flask, abort, flash, redirect, render_template, request, url_for

from train_model import FEATURES, MODEL_PATH, train_model


ROOT = Path(__file__).resolve().parent
DATABASE_DIR = ROOT / "database"
DATABASE_PATH = DATABASE_DIR / "students.db"
PARENTAL_EDUCATION = ["None", "High School", "Some College", "Bachelor", "Master"]
YES_NO = ["Yes", "No"]

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get(
    "FLASK_SECRET_KEY", "local-development-key-change-before-deployment"
)


@contextmanager
def get_connection():
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def init_db():
    DATABASE_DIR.mkdir(exist_ok=True)
    with get_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_name TEXT NOT NULL,
                study_hours REAL NOT NULL,
                attendance REAL NOT NULL,
                previous_marks REAL NOT NULL,
                assignment_marks REAL NOT NULL,
                sleep_hours REAL NOT NULL,
                parental_education TEXT NOT NULL,
                internet_access TEXT NOT NULL,
                extracurricular TEXT NOT NULL,
                predicted_marks REAL NOT NULL,
                category TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )


def load_model():
    if not MODEL_PATH.exists():
        train_model()
    bundle = joblib.load(MODEL_PATH)
    if not isinstance(bundle, dict) or "model" not in bundle:
        raise RuntimeError("The saved model artifact is invalid. Run python train_model.py again.")
    return bundle


MODEL_BUNDLE = load_model()


def category_for(marks):
    if marks >= 85:
        return "Excellent"
    if marks >= 70:
        return "Good"
    if marks >= 50:
        return "Average"
    return "Needs Improvement"


def suggestions_for(student, marks):
    suggestions = []
    if student["study_hours"] < 3:
        suggestions.append("Build a steady routine of at least 3 focused study hours a day.")
    if student["attendance"] < 80:
        suggestions.append("Improve class attendance and review notes after each lesson.")
    if student["previous_marks"] < 60:
        suggestions.append("Revisit foundational topics and schedule weekly practice tests.")
    if student["assignment_marks"] < 65:
        suggestions.append("Break assignments into smaller milestones and ask for feedback early.")
    if student["sleep_hours"] < 7:
        suggestions.append("Aim for 7–9 hours of sleep to support focus and memory.")
    if student["internet_access"] == "No":
        suggestions.append("Use the school library or download learning materials while connected.")
    if not suggestions and marks >= 85:
        suggestions.append("Excellent outlook—keep your balanced routine and challenge yourself.")
    if not suggestions:
        suggestions.append("Keep a consistent study schedule and track progress with weekly goals.")
    return suggestions


def parse_form(form):
    errors = []
    name = form.get("student_name", "").strip()
    if not name or len(name) > 80:
        errors.append("Enter a student name or ID (up to 80 characters).")

    numeric_specs = {
        "study_hours": ("Study hours per day", 0, 16),
        "attendance": ("Attendance percentage", 0, 100),
        "previous_marks": ("Previous exam marks", 0, 100),
        "assignment_marks": ("Assignment marks", 0, 100),
        "sleep_hours": ("Sleep hours", 0, 24),
    }
    values = {}
    for key, (label, minimum, maximum) in numeric_specs.items():
        raw = form.get(key, "").strip()
        try:
            value = float(raw)
            if not (minimum <= value <= maximum):
                raise ValueError
            values[key] = value
        except ValueError:
            errors.append(f"{label} must be a number from {minimum} to {maximum}.")

    parental = form.get("parental_education", "")
    internet = form.get("internet_access", "")
    extracurricular = form.get("extracurricular", "")
    if parental not in PARENTAL_EDUCATION:
        errors.append("Select a valid parental education level.")
    if internet not in YES_NO:
        errors.append("Select whether internet access is available.")
    if extracurricular not in YES_NO:
        errors.append("Select an extracurricular activity option.")
    values.update(
        {
            "student_name": name,
            "parental_education": parental,
            "internet_access": internet,
            "extracurricular": extracurricular,
        }
    )
    return values, errors


def predict_marks(student):
    frame = pd.DataFrame([{key: student[key] for key in FEATURES}], columns=FEATURES)
    prediction = float(MODEL_BUNDLE["model"].predict(frame)[0])
    return round(min(100.0, max(0.0, prediction)), 1)


def save_student(student, predicted_marks, record_id=None):
    now = datetime.now().astimezone().isoformat(timespec="seconds")
    values = (
        student["student_name"],
        student["study_hours"],
        student["attendance"],
        student["previous_marks"],
        student["assignment_marks"],
        student["sleep_hours"],
        student["parental_education"],
        student["internet_access"],
        student["extracurricular"],
        predicted_marks,
        category_for(predicted_marks),
        now,
    )
    with get_connection() as connection:
        if record_id is None:
            cursor = connection.execute(
                """
                INSERT INTO students (
                    student_name, study_hours, attendance, previous_marks,
                    assignment_marks, sleep_hours, parental_education,
                    internet_access, extracurricular, predicted_marks, category,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                values[:11] + (now, now),
            )
            return cursor.lastrowid
        connection.execute(
            """
            UPDATE students SET student_name=?, study_hours=?, attendance=?,
                previous_marks=?, assignment_marks=?, sleep_hours=?,
                parental_education=?, internet_access=?, extracurricular=?,
                predicted_marks=?, category=?, updated_at=? WHERE id=?
            """,
            values + (record_id,),
        )
    return record_id


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/dashboard")
def dashboard():
    with get_connection() as connection:
        rows = connection.execute("SELECT * FROM students ORDER BY created_at DESC").fetchall()
    marks = [row["predicted_marks"] for row in rows]
    categories = ["Excellent", "Good", "Average", "Needs Improvement"]
    distribution = {label: sum(row["category"] == label for row in rows) for label in categories}
    recent = rows[:5]
    trend = list(reversed(rows[:10]))
    return render_template(
        "dashboard.html",
        total=len(rows),
        average=round(sum(marks) / len(marks), 1) if marks else 0,
        distribution=distribution,
        trend=trend,
        recent=recent,
        model_name=MODEL_BUNDLE.get("model_name", "Regression model"),
        model_metrics=MODEL_BUNDLE.get("metrics", {}),
    )


@app.route("/predict", methods=["GET", "POST"])
def predict():
    student = {}
    if request.method == "POST":
        student, errors = parse_form(request.form)
        if errors:
            for error in errors:
                flash(error, "error")
            return render_template(
                "predict.html",
                student=student,
                parental_options=PARENTAL_EDUCATION,
                yes_no=YES_NO,
            ), 400
        predicted_marks = predict_marks(student)
        record_id = save_student(student, predicted_marks)
        flash("Prediction saved to the student records.", "success")
        return redirect(url_for("results", record_id=record_id))
    return render_template(
        "predict.html",
        student=student,
        parental_options=PARENTAL_EDUCATION,
        yes_no=YES_NO,
    )


@app.route("/results/<int:record_id>")
def results(record_id):
    with get_connection() as connection:
        student = connection.execute("SELECT * FROM students WHERE id=?", (record_id,)).fetchone()
    if student is None:
        abort(404)
    return render_template(
        "results.html",
        student=student,
        suggestions=suggestions_for(student, student["predicted_marks"]),
    )


@app.route("/students")
def students():
    search = request.args.get("q", "").strip()
    with get_connection() as connection:
        if search:
            rows = connection.execute(
                """SELECT * FROM students WHERE student_name LIKE ?
                   ORDER BY created_at DESC""",
                (f"%{search}%",),
            ).fetchall()
        else:
            rows = connection.execute("SELECT * FROM students ORDER BY created_at DESC").fetchall()
    return render_template("students.html", students=rows, search=search)


@app.route("/students/<int:record_id>/edit")
def edit_student(record_id):
    with get_connection() as connection:
        student = connection.execute("SELECT * FROM students WHERE id=?", (record_id,)).fetchone()
    if student is None:
        abort(404)
    return render_template(
        "predict.html",
        student=student,
        edit_mode=True,
        parental_options=PARENTAL_EDUCATION,
        yes_no=YES_NO,
    )


@app.route("/students/<int:record_id>/update", methods=["POST"])
def update_student(record_id):
    with get_connection() as connection:
        exists = connection.execute("SELECT id FROM students WHERE id=?", (record_id,)).fetchone()
    if exists is None:
        abort(404)
    student, errors = parse_form(request.form)
    if errors:
        for error in errors:
            flash(error, "error")
        return render_template(
            "predict.html",
            student=student,
            edit_mode=True,
            record_id=record_id,
            parental_options=PARENTAL_EDUCATION,
            yes_no=YES_NO,
        ), 400
    predicted_marks = predict_marks(student)
    save_student(student, predicted_marks, record_id)
    flash("Student record and prediction updated.", "success")
    return redirect(url_for("results", record_id=record_id))


@app.route("/students/<int:record_id>/delete", methods=["POST"])
def delete_student(record_id):
    with get_connection() as connection:
        cursor = connection.execute("DELETE FROM students WHERE id=?", (record_id,))
    if cursor.rowcount == 0:
        abort(404)
    flash("Student record deleted.", "success")
    return redirect(url_for("students"))


@app.errorhandler(404)
def not_found(_error):
    return render_template("index.html", not_found=True), 404


init_db()

if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG") == "1")
