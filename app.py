from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import check_password_hash
from database.database import get_db
from functools import wraps
from datetime import datetime

app = Flask(__name__)

app.secret_key = "smartcare-ai-secret-key"


# =========================================================
# LOGIN REQUIRED DECORATOR
# =========================================================

def login_required(role=None):

    def decorator(function):

        @wraps(function)
        def wrapper(*args, **kwargs):

            if "user_id" not in session:
                return redirect(url_for("login"))

            if role and session.get("role") != role:
                flash("Access denied.", "danger")
                return redirect(url_for("home"))

            return function(*args, **kwargs)

        return wrapper

    return decorator


# =========================================================
# HOME
# =========================================================

@app.route("/")
def home():

    return render_template("index.html")


# =========================================================
# LOGIN
# =========================================================

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form.get("username")
        password = request.form.get("password")
        role = request.form.get("role")

        db = get_db()

        user = db.execute(
            """
            SELECT * FROM users
            WHERE username = ? AND role = ?
            """,
            (username, role)
        ).fetchone()

        db.close()

        if user and check_password_hash(user["password"], password):

            session["user_id"] = user["id"]
            session["username"] = user["username"]
            session["role"] = user["role"]

            flash("Login successful!", "success")

            if role == "admin":
                return redirect(url_for("admin_dashboard"))

            elif role == "doctor":
                return redirect(url_for("doctor_dashboard"))

            elif role == "receptionist":
                return redirect(url_for("receptionist_dashboard"))

        flash("Invalid username, password or role.", "danger")

    return render_template("login.html")


# =========================================================
# LOGOUT
# =========================================================

@app.route("/logout")
def logout():

    session.clear()

    flash("You have been logged out.", "success")

    return redirect(url_for("login"))


# =========================================================
# ADMIN DASHBOARD
# =========================================================

@app.route("/admin/dashboard")
@login_required("admin")
def admin_dashboard():

    db = get_db()

    patients = db.execute(
        "SELECT COUNT(*) AS count FROM patients"
    ).fetchone()["count"]

    doctors = db.execute(
        "SELECT COUNT(*) AS count FROM doctors"
    ).fetchone()["count"]

    beds = db.execute(
        "SELECT COUNT(*) AS count FROM beds"
    ).fetchone()["count"]

    occupied_beds = db.execute(
        """
        SELECT COUNT(*) AS count
        FROM beds
        WHERE status = 'Occupied'
        """
    ).fetchone()["count"]

    db.close()

    stats = {
        "patients": patients,
        "doctors": doctors,
        "beds": beds,
        "occupied_beds": occupied_beds
    }

    predictions = {
        "op_patients": 455,
        "admissions": 43,
        "beds": 195,
        "doctors": 34,
        "waiting": 30,
        "icu": 92
    }

    return render_template(
        "admin/dashboard.html",
        stats=stats,
        predictions=predictions
    )


# =========================================================
# AI PREDICTIONS
# =========================================================

@app.route("/admin/predictions")
@login_required("admin")
def predictions():

    prediction_data = {
        "op_patients": 455,
        "admissions": 43,
        "beds": 195,
        "doctors": 34,
        "waiting": 30,
        "icu": 92
    }

    return render_template(
        "admin/predictions.html",
        predictions=prediction_data
    )


# =========================================================
# ANALYTICS
# =========================================================

@app.route("/admin/analytics")
@login_required("admin")
def analytics():

    db = get_db()

    rows = db.execute(
        """
        SELECT *
        FROM hospital_daily_data
        ORDER BY date DESC
        """
    ).fetchall()

    db.close()

    return render_template(
        "admin/analytics.html",
        rows=rows
    )


# =========================================================
# RECOMMENDATIONS
# =========================================================

@app.route("/admin/recommendations")
@login_required("admin")
def recommendations():

    recommendations_data = [

        {
            "priority": "HIGH",
            "message": "Increase doctor availability because predicted demand is high."
        },

        {
            "priority": "HIGH",
            "message": "Prepare additional beds for tomorrow's expected admissions."
        },

        {
            "priority": "CRITICAL",
            "message": "ICU occupancy is expected to reach 92%. Monitor ICU resources closely."
        },

        {
            "priority": "MEDIUM",
            "message": "Increase reception staff during peak hours to reduce waiting time."
        }

    ]

    return render_template(
        "admin/recommendations.html",
        recommendations=recommendations_data
    )


# =========================================================
# RESOURCES
# =========================================================

@app.route("/admin/resources")
@login_required("admin")
def resources():

    db = get_db()

    doctors = db.execute(
        "SELECT * FROM doctors"
    ).fetchall()

    beds = db.execute(
        "SELECT * FROM beds"
    ).fetchall()

    db.close()

    return render_template(
        "admin/resources.html",
        doctors=doctors,
        beds=beds
    )


# =========================================================
# REPORTS
# =========================================================

@app.route("/admin/reports")
@login_required("admin")
def reports():

    return render_template("admin/reports.html")


# =========================================================
# ADMIN PROFILE
# =========================================================

@app.route("/admin/profile")
@login_required("admin")
def admin_profile():

    return render_template("admin/profile.html")


# =========================================================
# DOCTOR DASHBOARD
# =========================================================

@app.route("/doctor/dashboard")
@login_required("doctor")
def doctor_dashboard():

    db = get_db()

    patients = db.execute(
        """
        SELECT DISTINCT p.*
        FROM patients p
        JOIN appointments a
        ON p.id = a.patient_id
        WHERE a.doctor_id = ?
        """,
        (session["user_id"],)
    ).fetchall()

    db.close()

    return render_template(
        "doctor/dashboard.html",
        patients=patients
    )


# =========================================================
# DOCTOR PATIENTS
# =========================================================

@app.route("/doctor/patients")
@login_required("doctor")
def doctor_patients():

    db = get_db()

    patients = db.execute(
        """
        SELECT DISTINCT p.*
        FROM patients p
        JOIN appointments a
        ON p.id = a.patient_id
        WHERE a.doctor_id = ?
        """,
        (session["user_id"],)
    ).fetchall()

    db.close()

    return render_template(
        "doctor/patients.html",
        patients=patients
    )


# =========================================================
# PATIENT HISTORY
# =========================================================

@app.route("/doctor/patient/<int:patient_id>")
@login_required("doctor")
def patient_history(patient_id):

    db = get_db()

    patient = db.execute(
        """
        SELECT *
        FROM patients
        WHERE id = ?
        """,
        (patient_id,)
    ).fetchone()

    treatments = db.execute(
        """
        SELECT *
        FROM treatments
        WHERE patient_id = ?
        ORDER BY date DESC
        """,
        (patient_id,)
    ).fetchall()

    db.close()

    return render_template(
        "doctor/patient_history.html",
        patient=patient,
        treatments=treatments
    )


# =========================================================
# DOCTOR TREATMENT
# =========================================================

@app.route("/doctor/treatment/<int:patient_id>", methods=["GET", "POST"])
@login_required("doctor")
def treatment(patient_id):

    db = get_db()

    patient = db.execute(
        """
        SELECT *
        FROM patients
        WHERE id = ?
        """,
        (patient_id,)
    ).fetchone()

    if request.method == "POST":

        diagnosis = request.form.get("diagnosis")
        prescription = request.form.get("prescription")
        treatment_text = request.form.get("treatment")
        follow_up = request.form.get("follow_up")

        doctor = db.execute(
            """
            SELECT id
            FROM doctors
            LIMIT 1
            """
        ).fetchone()

        doctor_id = doctor["id"] if doctor else 1

        db.execute(
            """
            INSERT INTO treatments
            (
                patient_id,
                doctor_id,
                date,
                diagnosis,
                prescription,
                treatment,
                follow_up
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                patient_id,
                doctor_id,
                datetime.now().strftime("%Y-%m-%d"),
                diagnosis,
                prescription,
                treatment_text,
                follow_up
            )
        )

        db.commit()
        db.close()

        flash("Treatment saved successfully.", "success")

        return redirect(
            url_for(
                "patient_history",
                patient_id=patient_id
            )
        )

    db.close()

    return render_template(
        "doctor/treatment.html",
        patient=patient
    )


# =========================================================
# DOCTOR PROFILE
# =========================================================

@app.route("/doctor/profile")
@login_required("doctor")
def doctor_profile():

    return render_template("doctor/profile.html")


# =========================================================
# RECEPTIONIST DASHBOARD
# =========================================================

@app.route("/receptionist/dashboard")
@login_required("receptionist")
def receptionist_dashboard():

    db = get_db()

    patients = db.execute(
        "SELECT * FROM patients ORDER BY id DESC"
    ).fetchall()

    beds = db.execute(
        """
        SELECT *
        FROM beds
        WHERE status = 'Available'
        """
    ).fetchall()

    db.close()

    return render_template(
        "receptionist/dashboard.html",
        patients=patients,
        beds=beds
    )


# =========================================================
# RECEPTIONIST PATIENTS
# =========================================================

@app.route("/receptionist/patients")
@login_required("receptionist")
def receptionist_patients():

    db = get_db()

    patients = db.execute(
        """
        SELECT *
        FROM patients
        ORDER BY id DESC
        """
    ).fetchall()

    db.close()

    return render_template(
        "receptionist/patients.html",
        patients=patients
    )


# =========================================================
# REGISTER PATIENT
# =========================================================

@app.route("/receptionist/register-patient", methods=["GET", "POST"])
@login_required("receptionist")
def register_patient():

    if request.method == "POST":

        name = request.form.get("name")
        age = request.form.get("age")
        gender = request.form.get("gender")
        phone = request.form.get("phone")
        address = request.form.get("address")

        db = get_db()

        db.execute(
            """
            INSERT INTO patients
            (
                name,
                age,
                gender,
                phone,
                address
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                name,
                age,
                gender,
                phone,
                address
            )
        )

        db.commit()
        db.close()

        flash("Patient registered successfully.", "success")

        return redirect(
            url_for("receptionist_patients")
        )

    return render_template(
        "receptionist/register_patient.html"
    )


# =========================================================
# APPOINTMENTS
# =========================================================

@app.route("/receptionist/appointments", methods=["GET", "POST"])
@login_required("receptionist")
def appointments():

    db = get_db()

    if request.method == "POST":

        patient_id = request.form.get("patient_id")
        doctor_id = request.form.get("doctor_id")
        appointment_date = request.form.get("appointment_date")
        appointment_time = request.form.get("appointment_time")

        db.execute(
            """
            INSERT INTO appointments
            (
                patient_id,
                doctor_id,
                appointment_date,
                appointment_time,
                status
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                patient_id,
                doctor_id,
                appointment_date,
                appointment_time,
                "Scheduled"
            )
        )

        db.commit()

        flash("Appointment booked successfully.", "success")

    patients = db.execute(
        "SELECT * FROM patients ORDER BY name"
    ).fetchall()

    doctors = db.execute(
        "SELECT * FROM doctors ORDER BY name"
    ).fetchall()

    appointments_data = db.execute(
        """
        SELECT
            a.*,
            p.name AS patient_name,
            d.name AS doctor_name
        FROM appointments a
        JOIN patients p
        ON a.patient_id = p.id
        JOIN doctors d
        ON a.doctor_id = d.id
        ORDER BY a.appointment_date DESC
        """
    ).fetchall()

    db.close()

    return render_template(
        "receptionist/appointments.html",
        patients=patients,
        doctors=doctors,
        appointments=appointments_data
    )


# =========================================================
# ADMISSIONS
# =========================================================

@app.route("/receptionist/admissions", methods=["GET", "POST"])
@login_required("receptionist")
def admissions():

    db = get_db()

    if request.method == "POST":

        patient_id = request.form.get("patient_id")
        bed_id = request.form.get("bed_id")
        reason = request.form.get("reason")

        admission_date = datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        db.execute(
            """
            INSERT INTO admissions
            (
                patient_id,
                bed_id,
                admission_date,
                reason,
                status
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                patient_id,
                bed_id,
                admission_date,
                reason,
                "Admitted"
            )
        )

        db.execute(
            """
            UPDATE beds
            SET status = 'Occupied'
            WHERE id = ?
            """,
            (bed_id,)
        )

        db.commit()

        flash("Patient admitted successfully.", "success")

    patients = db.execute(
        "SELECT * FROM patients ORDER BY name"
    ).fetchall()

    beds = db.execute(
        """
        SELECT *
        FROM beds
        WHERE status = 'Available'
        """
    ).fetchall()

    admissions_data = db.execute(
        """
        SELECT
            a.*,
            p.name AS patient_name,
            b.bed_number
        FROM admissions a
        JOIN patients p
        ON a.patient_id = p.id
        JOIN beds b
        ON a.bed_id = b.id
        ORDER BY a.admission_date DESC
        """
    ).fetchall()

    db.close()

    return render_template(
        "receptionist/admissions.html",
        patients=patients,
        beds=beds,
        admissions=admissions_data
    )


# =========================================================
# RECEPTIONIST PROFILE
# =========================================================

@app.route("/receptionist/profile")
@login_required("receptionist")
def receptionist_profile():

    return render_template(
        "receptionist/profile.html"
    )


# =========================================================
# RUN APPLICATION
# =========================================================

if __name__ == "__main__":
    app.run(debug=True)