import sqlite3
import os
from werkzeug.security import generate_password_hash

# Create database folder if it does not exist
os.makedirs("database", exist_ok=True)

DATABASE = "database/smartcare.db"

connection = sqlite3.connect(DATABASE)
cursor = connection.cursor()

# Users table
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    role TEXT NOT NULL
)
""")

# Patients table
cursor.execute("""
CREATE TABLE IF NOT EXISTS patients (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    age INTEGER,
    gender TEXT,
    phone TEXT,
    address TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

# Doctors table
cursor.execute("""
CREATE TABLE IF NOT EXISTS doctors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    specialization TEXT,
    phone TEXT
)
""")

# Appointments table
cursor.execute("""
CREATE TABLE IF NOT EXISTS appointments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id INTEGER NOT NULL,
    doctor_id INTEGER NOT NULL,
    appointment_date TEXT NOT NULL,
    appointment_time TEXT NOT NULL,
    status TEXT DEFAULT 'Scheduled',
    FOREIGN KEY (patient_id) REFERENCES patients(id),
    FOREIGN KEY (doctor_id) REFERENCES doctors(id)
)
""")

# Beds table
cursor.execute("""
CREATE TABLE IF NOT EXISTS beds (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    bed_number TEXT UNIQUE NOT NULL,
    bed_type TEXT NOT NULL,
    status TEXT DEFAULT 'Available'
)
""")

# Admissions table
cursor.execute("""
CREATE TABLE IF NOT EXISTS admissions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id INTEGER NOT NULL,
    bed_id INTEGER NOT NULL,
    admission_date TEXT DEFAULT CURRENT_TIMESTAMP,
    reason TEXT,
    status TEXT DEFAULT 'Admitted',
    FOREIGN KEY (patient_id) REFERENCES patients(id),
    FOREIGN KEY (bed_id) REFERENCES beds(id)
)
""")

# Treatments table
cursor.execute("""
CREATE TABLE IF NOT EXISTS treatments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id INTEGER NOT NULL,
    doctor_id INTEGER NOT NULL,
    date TEXT DEFAULT CURRENT_TIMESTAMP,
    diagnosis TEXT,
    prescription TEXT,
    treatment TEXT,
    follow_up TEXT,
    FOREIGN KEY (patient_id) REFERENCES patients(id),
    FOREIGN KEY (doctor_id) REFERENCES doctors(id)
)
""")

# Insert users
users = [
    ("admin", generate_password_hash("admin123"), "admin"),
    ("doctor", generate_password_hash("doctor123"), "doctor"),
    ("reception", generate_password_hash("reception123"), "receptionist")
]

for user in users:
    cursor.execute("""
    INSERT OR IGNORE INTO users (username, password, role)
    VALUES (?, ?, ?)
    """, user)

# Insert doctors
doctors = [
    ("Dr. Raj Kumar", "General Medicine", "9876543210"),
    ("Dr. Priya Sharma", "Cardiology", "9876543211"),
    ("Dr. Rahul Reddy", "Orthopedics", "9876543212")
]

for doctor in doctors:
    cursor.execute("""
    INSERT OR IGNORE INTO doctors (name, specialization, phone)
    VALUES (?, ?, ?)
    """, doctor)

# Insert beds
for i in range(1, 51):
    cursor.execute("""
    INSERT OR IGNORE INTO beds (bed_number, bed_type, status)
    VALUES (?, ?, ?)
    """, (f"B-{i:03d}", "General", "Available"))

connection.commit()
connection.close()

print("Database initialized successfully!")