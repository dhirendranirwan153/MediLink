import os
import random
import string
from flask import Flask, render_template, request, redirect, url_for
# Import the database object from your models.py
from models import db,  User, DoctorProfile, PatientProfile, ClinicalEntry, PatientReport, AccessGrant
from werkzeug.utils import secure_filename
from flask_bcrypt import Bcrypt
from flask import session
from flask import send_from_directory
import matplotlib.pyplot as plt
import io
import base64
import qrcode


app = Flask(__name__)
bcrypt = Bcrypt(app)    # Initialize Bcrypt here
app.secret_key = 'your_super_secret_key_here'

# --- DATABASE CONFIGURATION (Paste here) ---
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'medilink.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# 1. Define the absolute path to your project folder
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads')

# 2. Configure Flask
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['ALLOWED_EXTENSIONS'] = {'pdf', 'png', 'jpg', 'jpeg', 'xls', 'xlsx'}

# 3. Create the folder automatically if it’s missing (Double-check)
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

# Connect the database to the app
db.init_app(app)

# Create the physical .db file
with app.app_context():
    db.create_all()
# --------------------------------------------


@app.route('/')
def index():
    return render_template ('home.html')

@app.route('/sign_up')
def sign_up():
    return render_template ('role.html')

@app.route('/services')
def services():
    return render_template ('services2.html')

@app.route('/about')
def about():
    return render_template ('about2.html')

@app.route('/contact')
def contact():
    return render_template ('contact.html')

@app.route("/terms&cond.")
def terms():
    return render_template ('terms&cond.html')

# Define the helper function BEFORE the routes
def generate_medilink_id(role):
    prefix = "MLP" if role == "patient" else "MLD"
    random_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
    return f"{prefix}-2026-{random_str}"

@app.route('/doctor_register', methods=['GET', 'POST'])
def doctor_register():
    if request.method == 'POST':
        # 1. Grab data using Saloni's exact 'name' attributes
        fname = request.form.get('fform')
        lname = request.form.get('lform')
        email = request.form.get('eform')
        password = request.form.get('pform')
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        phone = request.form.get('Phone')
        reg_no = request.form.get('R_no')
        hospital = request.form.get('hospital')
        spec = request.form.get('specialization')

        # 2. Generate Unique Doctor ID (MLD-2026-XXXX)
        m_id = generate_medilink_id('doctor')

        try:
            # 3. Create Base User
            new_user = User(
                medilink_id=m_id, 
                name=f"{fname} {lname}", 
                email=email, 
                password=hashed_password, # <--- Save the hash, not the plain text! 
                role='doctor'
            )
            db.session.add(new_user)
            db.session.flush() # Get user.id for the profile link

            # 4. Create Doctor Profile
            new_profile = DoctorProfile(
                user_id=new_user.id,
                reg_no=reg_no,
                specialization=spec,
                hospital=hospital
            )
            db.session.add(new_profile)
            db.session.commit()

            # 5. Reuse the same success page!
            return render_template('success.html', user_id=m_id)

        except Exception as e:
            db.session.rollback()
            return f"Database Error: {str(e)}"

    return render_template('Doctor_register.html')


@app.route('/doctor_login', methods=['GET', 'POST'])
def doctor_login():
    if request.method == 'POST':
        # 1. Grab email and password from the DOCTOR login form
        email = request.form.get('eform') 
        password = request.form.get('pform')

        # 2. Find the user in the database with role 'doctor'
        user = User.query.filter_by(email=email, role='doctor').first()

        # 3. Verify existence and check the hashed password
        if user and bcrypt.check_password_hash(user.password, password):
            # SAVE the user's database ID in the session
            session['user_id'] = user.id
            # SUCCESS! Redirect to the Doctor Dashboard
            return redirect(url_for('doctor_dashboard'))
        else:
            # FAIL!
            return "Invalid Doctor Credentials. Please check your email/password."

    return render_template('doctor_login.html')

# Placeholder for the Doctor Dashboard redirect
@app.route('/doctor_dashboard')
def doctor_dashboard():
    # 1. Check if a user is actually logged in
    if 'user_id' not in session:
        return redirect(url_for('doctor_login'))

    # 2. Get the current doctor's data from the database
    doctor_user = User.query.get(session['user_id'])
    doctor_profile = DoctorProfile.query.filter_by(user_id=doctor_user.id).first()

    # 3. Fetch the 5 most recent unique patients this doctor has treated
    # We query the ClinicalEntry table and group by patient_id
    recent_entries = ClinicalEntry.query.filter_by(doctor_id=doctor_user.medilink_id)\
                     .order_by(ClinicalEntry.id.desc()).limit(10).all()

    # 4. To avoid duplicates in the "Recent" list, let's get unique IDs
    recent_patients_list = []
    seen_ids = set()
    for entry in recent_entries:
        if entry.patient_id not in seen_ids:
            recent_patients_list.append(entry)
            seen_ids.add(entry.patient_id)
            if len(recent_patients_list) == 5: # Just show top 5
                break

    # 3. Pass that data to the HTML template
    return render_template('doctor_dashboard.html', doctor=doctor_user, profile=doctor_profile, recent_patients=recent_patients_list)






@app.route('/patient_register', methods=['GET', 'POST'])
def patient_register():
    if request.method == 'POST':
        # Use the EXACT names from Saloni's HTML
        fname = request.form.get('fform') # Matches name="fform"
        lname = request.form.get('lform') # Matches name="lform"
        email = request.form.get('eform') # Matches name="eform"
        password = request.form.get('pform') # Matches name="pform"
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        phone = request.form.get('Phone') # Matches name="Phone"
        dob = request.form.get('dob') # Matches name="dob"
        print(f"Captured DOB: {dob}")

        # Generate the Unique ID
        m_id = generate_medilink_id('patient')
        
        # Save to Database
        try:
            new_user = User(
                medilink_id=m_id, 
                name=f"{fname} {lname}", 
                email=email, 
                password=hashed_password, # <--- Save the hash, not the plain text!
                role='patient'
            )
            db.session.add(new_user)
            db.session.flush() # Get user ID before final commit
            
            new_profile = PatientProfile(user_id=new_user.id, dob=dob)
            db.session.add(new_profile)
            
            db.session.commit()
            return render_template('success.html', user_id=m_id)
            
        except Exception as e:
            db.session.rollback()
            return f"Error: {str(e)}"

    return render_template('patient_register.html')



@app.route('/patient_login', methods=['GET', 'POST'])
def patient_login():
    if request.method == 'POST':
        session.clear() # <--- Add this! Kick out any logged-in Doctor first.
        email = request.form.get('eform')
        password = request.form.get('pform')
        
        user = User.query.filter_by(email=email, role='patient').first()
        
        if user and bcrypt.check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['role'] = 'patient' # Good practice to store the role too
            return redirect(url_for('patient_dashboard'))
        
        return "Invalid Credentials. Please check email/password."
    
    return render_template('patient_login.html')

@app.route('/patient_dashboard')
def patient_dashboard():
    print(f"DEBUG: Session User ID is {session.get('user_id')}")
    
    if 'user_id' not in session:
        print("DEBUG: No user_id in session, redirecting to login.")
        return redirect(url_for('patient_login'))

    patient_user = User.query.filter_by(id=session['user_id'], role='patient').first()
    
    if not patient_user:
        print(f"DEBUG: User found in DB but role is NOT patient. Redirecting.")
        return redirect(url_for('patient_login'))

    # If it passes those, it will show the dashboard
    medical_history = ClinicalEntry.query.filter_by(patient_id=patient_user.medilink_id).all()
    latest_entry = ClinicalEntry.query.filter_by(patient_id=patient_user.medilink_id).order_by(ClinicalEntry.id.desc()).first()

    # Fetch all uploaded reports (PDFs, Excel, etc.)
    reports = PatientReport.query.filter_by(patient_id=patient_user.medilink_id).all()

    # NEW: Fetch all active access grants for this patient
    grants = AccessGrant.query.filter_by(patient_id=patient_user.medilink_id).all()

    # --- Strict QR Generation ---
    try:
        qr = qrcode.QRCode(version=1, box_size=5, border=2) # Slightly smaller for better fit
        qr.add_data(patient_user.medilink_id)
        qr.make(fit=True)
        
        # We explicitly use the default pil factory
        img = qr.make_image(fill_color="black", back_color="white")
        
        buf = io.BytesIO()
        img.save(buf, format='PNG')
        buf.seek(0)  # Go back to the start of the buffer
        
        qr_bytes = buf.read()
        qr_base64 = base64.b64encode(qr_bytes).decode('utf-8')
        
        print(f"DEBUG: QR Code successfully generated! Length: {len(qr_base64)}")
        
    except Exception as e:
        print(f"QR ERROR: {str(e)}")
        qr_base64 = ""
    
    return render_template('patient_dashboard.html', 
                           patient=patient_user, 
                           history=medical_history, 
                           reports=reports, 
                           latest=latest_entry,
                           grants=grants,
                           qr_code=qr_base64) # Pass it to the frontend

    

@app.route('/add_entry', methods=['POST'])
def add_entry():
    if 'user_id' not in session:
        return redirect(url_for('doctor_login'))

    # 1. Get the Doctor's ID from the session to identify who is writing the report
    doctor_user = User.query.get(session['user_id'])
    
    # 2. Grab data from the Box 5 form
    patient_id = request.form.get('p_id') # The MLP-ID of the patient
    entry_date = request.form.get('entry_date')
    symptoms = request.form.get('symptoms')
    diagnosis = request.form.get('diagnosis')
    
    # Combine vitals into one string for easier storage
    bp = request.form.get('bp')
    sugar = request.form.get('sugar')
    weight = request.form.get('weight')
    vitals_combined = f"BP: {bp}, Sugar: {sugar}, Weight: {weight}"
    
    prescription = request.form.get('prescription')

    # 3. Save to the ClinicalEntry table
    try:
        new_entry = ClinicalEntry(
            patient_id=patient_id,
            doctor_id=doctor_user.medilink_id, # The doctor's MLD ID
            date=entry_date,
            symptoms=symptoms,
            diagnosis=diagnosis,
            vitals=vitals_combined,
            prescription=prescription
        )
        db.session.add(new_entry)
        db.session.commit()
        return f"Entry saved successfully for Patient {patient_id}!"
    
    except Exception as e:
        db.session.rollback()
        return f"Error saving entry: {str(e)}"
    
@app.route('/upload_report', methods=['POST'])
def upload_report():
    if 'user_id' not in session or session.get('role') != 'patient':
        return redirect(url_for('patient_login'))
    
    patient = User.query.get(session['user_id'])
    
    if 'file' not in request.files:
        return "No file part"
    
    file = request.files['file']
    description = request.form.get('description')

    if file and file.filename != '':
        # Secure the filename to prevent directory injection attacks
        filename = secure_filename(file.filename)
        # Rename file to include Patient ID to avoid overwriting others
        unique_name = f"{patient.medilink_id}_{filename}"
        
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], unique_name))
        
        # Save reference to the DB
        new_report = PatientReport(
            patient_id=patient.medilink_id,
            file_name=unique_name,
            description=description
        )
        db.session.add(new_report)
        db.session.commit()
        
        return redirect(url_for('patient_dashboard'))
    
    return "Upload failed" 

@app.route('/view_file/<filename>')
def view_file(filename):
    # This ensures Flask looks exactly where the file is stored
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/delete_report/<int:report_id>')
def delete_report(report_id):
    if 'user_id' not in session:
        return redirect(url_for('patient_login'))

    # 1. Find the report in the database
    report = PatientReport.query.get(report_id)
    
    if report:
        # 2. Get the physical path of the file
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], report.file_name)
        
        try:
            # 3. Physically delete the file from the 'uploads' folder
            if os.path.exists(file_path):
                os.remove(file_path)
            
            # 4. Remove the entry from the database
            db.session.delete(report)
            db.session.commit()
            return redirect(url_for('patient_dashboard'))
        except Exception as e:
            return f"Error deleting file: {str(e)}"
    
    return "Report not found"

@app.route('/search_patient', methods=['POST'])
def search_patient():
    if 'user_id' not in session:
        return redirect(url_for('doctor_login'))

    #  Fetch the doctor and explicitly verify they exist
    doctor = User.query.get(session['user_id'])
    
    if not doctor:
        return redirect(url_for('doctor_login'))

    patient_id = request.form.get('patient_id').strip()
    
    #  Check permission using the doctor's medilink_id
    # If the yellow line persists, you can use doctor.medilink_id directly
    permission = AccessGrant.query.filter_by(
        patient_id=patient_id, 
        doctor_id=doctor.medilink_id, 
        status='granted'
    ).first()

    if not permission:
        return "<h3>Access Denied: This patient hasn't authorized you yet.</h3>"

    # ... rest of your code to fetch patient, history, and reports
    # 2. Find the Patient
    patient = User.query.filter_by(medilink_id=patient_id, role='patient').first()
    
    if not patient:
        return "<h3>Patient ID not found. Please check the ID and try again.</h3>"

    # 3. Get their History (Doctor Notes)
    history = ClinicalEntry.query.filter_by(patient_id=patient_id).all()
    
    # 4. Get their Uploaded Reports (PDFs/Excel)
    reports = PatientReport.query.filter_by(patient_id=patient_id).all()

    # 5.Generate the graph
    graph_data = generate_vitals_plot(history)

    return render_template('patient_profile_view.html', 
                           patient=patient, 
                           history=history, 
                           reports=reports,
                           graph=graph_data)

    

@app.route('/grant_access', methods=['POST'])
def grant_access():
    if 'user_id' not in session:
        return redirect(url_for('patient_login'))
    
    patient = User.query.get(session['user_id'])
    doctor_id = request.form.get('doctor_id').strip()

    # Verify if the Doctor ID actually exists
    doctor_exists = User.query.filter_by(medilink_id=doctor_id, role='doctor').first()
    if not doctor_exists:
        return "Doctor ID not found."

    # Create the grant
    new_grant = AccessGrant(patient_id=patient.medilink_id, doctor_id=doctor_id)
    db.session.add(new_grant)
    db.session.commit()
    
    return redirect(url_for('patient_dashboard'))

@app.route('/revoke_access/<int:grant_id>')
def revoke_access(grant_id):
    grant = AccessGrant.query.get(grant_id)
    if grant:
        db.session.delete(grant)
        db.session.commit()
    return redirect(url_for('patient_dashboard'))

def generate_vitals_plot(history):
    if not history:
        return None

    dates = [entry.date for entry in history]
    # Extracting Systolic BP (the first number) as an example
    try:
        bp_values = [int(entry.vitals.split(',')[0].split(':')[1].split('/')[0]) for entry in history]
    except:
        return None # In case data is formatted poorly

    plt.figure(figsize=(5, 4))
    plt.plot(dates, bp_values, marker='o', linestyle='-', color='teal')
    plt.title('Blood Pressure Trend')
    plt.xlabel('Date')
    plt.ylabel('Systolic BP (mmHg)')
    plt.xticks(rotation=45)
    plt.tight_layout()

    # Save plot to a buffer
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    img_base64 = base64.b64encode(buf.read()).decode('utf-8')
    plt.close()
    return img_base64

if __name__ == '__main__':
    app.run(debug=True)
