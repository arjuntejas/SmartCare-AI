
import os
import secrets
from pathlib import Path
from datetime import date, timedelta

from flask import (
    Flask,
    render_template,
    redirect,
    url_for,
    request,
    flash,
    jsonify,
)
from flask_login import (
    LoginManager,
    login_user,
    logout_user,
    login_required,
    current_user,
)
from flask_wtf.csrf import CSRFProtect

from models import db, Admin, HospitalDailyStats
from predictions import (
    predict_patient_demand,
    generate_resource_recommendations,
)


# --------------------------------------------------
# 1. APPLICATION CONFIGURATION
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent
INSTANCE_DIR = BASE_DIR / "instance"
INSTANCE_DIR.mkdir(exist_ok=True)

app = Flask(__name__, instance_path=str(INSTANCE_DIR))

app.config["SECRET_KEY"] = (
    os.environ.get("SECRET_KEY") or secrets.token_hex(32)
)

app.config["SQLALCHEMY_DATABASE_URI"] = (
    "sqlite:///" + (INSTANCE_DIR / "smartcare.db").as_posix()
)

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)
CSRFProtect(app)

login_manager = LoginManager()
login_manager.login_view = "login"
login_manager.init_app(app)


@login_manager.user_loader
def load_user(user_id):
    try:
        return db.session.get(Admin, int(user_id))
    except (TypeError, ValueError):
        return None


# --------------------------------------------------
# 2. SAMPLE HOSPITAL DATA
# --------------------------------------------------

def seed_demo_data():
    if HospitalDailyStats.query.first():
        return

    today = date.today()

    for days_ago in range(29, -1, -1):
        record_date = today - timedelta(days=days_ago)

        patients = 80 + ((days_ago * 7 + 13) % 55)
        total_beds = 150
        occupied_beds = min(total_beds, patients + 12)
        doctors = 18 + ((days_ago * 3) % 9)

        record = HospitalDailyStats(
            record_date=record_date,
            patients=patients,
            total_beds=total_beds,
            occupied_beds=occupied_beds,
            available_doctors=doctors,
        )

        db.session.add(record)

    db.session.commit()


with app.app_context():
    db.create_all()
    seed_demo_data()


# --------------------------------------------------
# 3. HOME PAGE
# --------------------------------------------------

@app.route("/")
def index():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))

    return redirect(url_for("login"))


# --------------------------------------------------
# 4. ADMIN REGISTRATION
# --------------------------------------------------

@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")

        if not name or not email or "@" not in email:
            flash("Enter a valid name and email address.", "error")

        elif Admin.query.filter_by(email=email).first():
            flash("An account with this email already exists.", "error")

        elif len(password) < 10:
            flash("Use a password with at least 10 characters.", "error")

        elif password != confirm:
            flash("Passwords do not match.", "error")

        else:
            admin = Admin(name=name, email=email)
            admin.set_password(password)

            db.session.add(admin)
            db.session.commit()

            flash("Account created. Please sign in.", "success")
            return redirect(url_for("login"))

    return render_template("register.html")


# --------------------------------------------------
# 5. ADMIN LOGIN
# --------------------------------------------------

@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        admin = Admin.query.filter_by(email=email).first()

        if admin and admin.check_password(password):
            login_user(admin)
            return redirect(url_for("dashboard"))

        flash("Incorrect email or password.", "error")

    return render_template("login.html")


# --------------------------------------------------
# 6. ADMIN LOGOUT
# --------------------------------------------------

# --------------------------------------------------
# ADMIN LOGOUT
# --------------------------------------------------

@app.route("/logout", methods=["GET", "POST"])
@login_required
def logout():
    logout_user()
    flash("You have been logged out successfully.", "success")
    return redirect(url_for("login"))


# --------------------------------------------------
# 7. DASHBOARD
# --------------------------------------------------


@app.route("/dashboard")
@login_required
def dashboard():
    latest = (
        HospitalDailyStats.query
        .order_by(HospitalDailyStats.record_date.desc())
        .first()
    )

    total_patients = latest.patients if latest else 0
    total_beds = latest.total_beds if latest else 0
    occupied_beds = latest.occupied_beds if latest else 0
    available_doctors = latest.available_doctors if latest else 0

    available_beds = max(total_beds - occupied_beds, 0)

    occupancy = (
        round((occupied_beds / total_beds) * 100, 1)
        if total_beds > 0
        else 0
    )

    return render_template(
        "dashboard.html",
        latest=latest,
        total_patients=total_patients,
        total_beds=total_beds,
        occupied_beds=occupied_beds,
        available_beds=available_beds,
        available_doctors=available_doctors,
        occupancy=occupancy,
        now_date=date.today().strftime("%d %b %Y"),
    )



# --------------------------------------------------
# 8. ANALYTICS API FOR CHARTS
# --------------------------------------------------

@app.route("/api/analytics")
@login_required
def analytics():
    start_date = date.today() - timedelta(days=29)

    records = (
        HospitalDailyStats.query
        .filter(HospitalDailyStats.record_date >= start_date)
        .order_by(HospitalDailyStats.record_date.asc())
        .all()
    )

    return jsonify({
        "labels": [
            record.record_date.strftime("%d %b")
            for record in records
        ],
        "patients": [
            record.patients for record in records
        ],
        "occupied_beds": [
            record.occupied_beds for record in records
        ],
        "available_beds": [
            max(
                record.total_beds - record.occupied_beds,
                0
            )
            for record in records
        ],
    })


# --------------------------------------------------
# 9. HOSPITAL RESOURCES: ADD AND VIEW RECORDS
# --------------------------------------------------

@app.route("/resources", methods=["GET", "POST"])
@login_required
def resources():
    if request.method == "POST":
        try:
            record_date = date.fromisoformat(
                request.form.get("record_date", "").strip()
            )

            patients = int(request.form.get("patients", "0"))
            total_beds = int(request.form.get("total_beds", "0"))
            occupied_beds = int(
                request.form.get("occupied_beds", "0")
            )
            doctors = int(
                request.form.get("available_doctors", "0")
            )

            # Validate entered values.
            if min(
                patients,
                total_beds,
                occupied_beds,
                doctors,
            ) < 0:
                raise ValueError("Values cannot be negative.")

            if occupied_beds > total_beds:
                raise ValueError(
                    "Occupied beds cannot exceed total beds."
                )

            # Update the record if this date already exists.
            record = HospitalDailyStats.query.filter_by(
                record_date=record_date
            ).first()

            if record:
                record.patients = patients
                record.total_beds = total_beds
                record.occupied_beds = occupied_beds
                record.available_doctors = doctors

            else:
                record = HospitalDailyStats(
                    record_date=record_date,
                    patients=patients,
                    total_beds=total_beds,
                    occupied_beds=occupied_beds,
                    available_doctors=doctors,
                )

                db.session.add(record)

            db.session.commit()

            flash(
                "Hospital record saved successfully.",
                "success",
            )

            return redirect(url_for("resources"))

        except ValueError:
            db.session.rollback()

            flash(
                "Enter a valid date and non-negative whole numbers. "
                "Occupied beds cannot exceed total beds.",
                "error",
            )

    records = (
        HospitalDailyStats.query
        .order_by(HospitalDailyStats.record_date.desc())
        .limit(30)
        .all()
    )

    return render_template(
        "resources.html",
        records=records,
        today=date.today().isoformat(),
    )


# --------------------------------------------------
# 10. START THE FLASK SERVER
# IMPORTANT: KEEP THIS BLOCK AT THE VERY BOTTOM.
# --------------------------------------------------


# --------------------------------------------------
# AI PATIENT DEMAND PREDICTION
# --------------------------------------------------

@app.route("/prediction")
@login_required
def prediction():
    result = predict_patient_demand(days_ahead=7)
    resource_result = generate_resource_recommendations()

    return render_template(
        "prediction.html",
        result=result,
        resource_result=resource_result,
    )


if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True,
    )
