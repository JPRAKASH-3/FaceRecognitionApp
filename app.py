import os
import uuid
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, Response, jsonify, flash
import pandas as pd
import face_recognition
import cv2
import numpy as np
from werkzeug.utils import secure_filename
import openpyxl

# ---------------- CONFIG ----------------
APP_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(APP_DIR, "uploads")     # store registered images
EXCEL_USERS = os.path.join(APP_DIR, "users.xlsx")    # registered users
EXCEL_ATTEND = os.path.join(APP_DIR, "attendance.xlsx")  # attendance log
ALLOWED_EXT = {"png", "jpg", "jpeg"}
PORT = 5001

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app = Flask(__name__)
app.secret_key = "supersecret"
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# ---------------- EXCEL INIT ----------------
def init_excels():
    # users.xlsx
    if not os.path.exists(EXCEL_USERS):
        df = pd.DataFrame(columns=["user_id", "name", "role", "timestamp", "image_path"])
        df.to_excel(EXCEL_USERS, index=False)

    # attendance.xlsx
    if not os.path.exists(EXCEL_ATTEND):
        wb = openpyxl.Workbook()
        sheet = wb.active
        sheet.title = "Attendance"
        sheet.append(["Name", "Role", "Date", "Time", "Status"])
        wb.save(EXCEL_ATTEND)

init_excels()

# ---------------- USER HANDLING ----------------
def add_user(name, role, filename):
    df = pd.read_excel(EXCEL_USERS)
    user_id = str(uuid.uuid4())[:8]
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    relpath = os.path.join("uploads", filename)
    new_user = {"user_id": user_id, "name": name, "role": role,
                "timestamp": now, "image_path": relpath}
    df = pd.concat([df, pd.DataFrame([new_user])], ignore_index=True)
    df.to_excel(EXCEL_USERS, index=False)

def mark_attendance(name, role, status="Recognized"):
    wb = openpyxl.load_workbook(EXCEL_ATTEND)
    sheet = wb.active
    now = datetime.now()
    date = now.strftime("%Y-%m-%d")
    time = now.strftime("%H:%M:%S")
    sheet.append([name, role, date, time, status])
    wb.save(EXCEL_ATTEND)

# ---------------- FACE DATA ----------------
known_encodings = []
known_names = []
known_roles = []

def load_registered_faces():
    global known_encodings, known_names, known_roles
    known_encodings, known_names, known_roles = [], [], []
    for fname in os.listdir(UPLOAD_FOLDER):
        path = os.path.join(UPLOAD_FOLDER, fname)
        if not any(fname.lower().endswith(ext) for ext in ALLOWED_EXT):
            continue
        try:
            img = face_recognition.load_image_file(path)
            encoding = face_recognition.face_encodings(img)[0]
            parts = fname.split("_")  # Example: John_Student.jpg
            name = parts[0]
            role = parts[1].split(".")[0] if len(parts) > 1 else "-"
            known_encodings.append(encoding)
            known_names.append(name)
            known_roles.append(role)
        except Exception as e:
            print("Skipping file", fname, "->", e)

load_registered_faces()

# ---------------- VIDEO STREAM ----------------
def generate_frames():
    camera = cv2.VideoCapture(0)
    while True:
        success, frame = camera.read()
        if not success:
            break

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        faces = face_recognition.face_locations(rgb)
        encodings = face_recognition.face_encodings(rgb, faces)

        for (top, right, bottom, left), encoding in zip(faces, encodings):
            matches = face_recognition.compare_faces(known_encodings, encoding, tolerance=0.5)
            name, role = "Unknown", "-"
            if True in matches:
                idx = matches.index(True)
                name = known_names[idx]
                role = known_roles[idx]
                mark_attendance(name, role, "Recognized")
            else:
                mark_attendance("Unknown", "-", "Unrecognized")

            cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 0), 2)
            cv2.putText(frame, f"{name} ({role})", (left, top - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

        ret, buffer = cv2.imencode(".jpg", frame)
        frame = buffer.tobytes()
        yield (b"--frame\r\n"
               b"Content-Type: image/jpeg\r\n\r\n" + frame + b"\r\n")

# ---------------- ROUTES ----------------
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/video_feed")
def video_feed():
    return Response(generate_frames(), mimetype="multipart/x-mixed-replace; boundary=frame")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form["name"]
        role = request.form["role"]
        photo = request.files["photo"]
        if name and role and photo:
            filename = f"{name}_{role}.jpg"
            path = os.path.join(UPLOAD_FOLDER, filename)
            photo.save(path)
            add_user(name, role, filename)
            load_registered_faces()
            flash("Registration successful!", "success")
            return redirect(url_for("index"))
    return render_template("register.html")

@app.route("/admin")
def admin():
    df = pd.read_excel(EXCEL_ATTEND)
    data = df.to_dict(orient="records")
    return render_template("admin.html", data=data)

# ---------------- MAIN ----------------
if __name__ == "__main__":
    app.run(debug=True, port=PORT)
