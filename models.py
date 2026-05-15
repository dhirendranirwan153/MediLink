from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    medilink_id = db.Column(db.String(20), unique=True, nullable=False) # Your unique generated ID
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(10), nullable=False) # 'doctor' or 'patient'

class DoctorProfile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    reg_no = db.Column(db.String(50), nullable=False)
    specialization = db.Column(db.String(100), nullable=False)
    hospital = db.Column(db.String(100), nullable=False)

class PatientProfile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    dob = db.Column(db.String(20), nullable=False)

class ClinicalEntry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.String(20), nullable=False) # The MLP-ID of the patient
    doctor_id = db.Column(db.String(20), nullable=False)  # The MLD-ID of the doctor
    date = db.Column(db.String(20))
    symptoms = db.Column(db.Text)
    diagnosis = db.Column(db.Text)
    vitals = db.Column(db.String(100)) # Store as "BP: 120/80, Sugar: 90"
    prescription = db.Column(db.Text)  

class PatientReport(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.String(20), nullable=False) # Linked to MLP-ID
    file_name = db.Column(db.String(100), nullable=False) # e.g., "blood_test.pdf"
    description = db.Column(db.String(100))
    upload_date = db.Column(db.DateTime, default=db.func.current_timestamp())

class AccessGrant(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.String(20), nullable=False) # MLP-ID
    doctor_id = db.Column(db.String(20), nullable=False)  # MLD-ID
    status = db.Column(db.String(20), default='granted') # 'granted' or 'revoked'    

# REMEMBER: Import this in app.py and run db.create_all()!      