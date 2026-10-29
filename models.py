
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

# Initialize the database
db = SQLAlchemy()


# Administrator account model
class Admin(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(
        db.String(100),
        nullable=False
    )

    email = db.Column(
        db.String(120),
        unique=True,
        nullable=False
    )

    password_hash = db.Column(
        db.String(256),
        nullable=False
    )

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(
            self.password_hash,
            password
        )


# Daily hospital statistics model
class HospitalDailyStats(db.Model):
    id = db.Column(
        db.Integer,
        primary_key=True
    )

    record_date = db.Column(
        db.Date,
        unique=True,
        nullable=False
    )

    patients = db.Column(
        db.Integer,
        default=0
    )

    total_beds = db.Column(
        db.Integer,
        default=0
    )

    occupied_beds = db.Column(
        db.Integer,
        default=0
    )

    available_doctors = db.Column(
        db.Integer,
        default=0
    )
