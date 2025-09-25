from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, Response
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import json
import os
import hashlib

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'metawell-clinic-secret-2024')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///clinic.db').replace('postgres://', 'postgresql://')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'

# Database Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(20), default='receptionist')  # admin, doctor, nurse, receptionist
    full_name = db.Column(db.String(100))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Patient(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.String(20), unique=True, nullable=False)
    phone_number = db.Column(db.String(20), unique=True, nullable=False)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    id_number = db.Column(db.String(20), unique=True)
    date_of_birth = db.Column(db.Date)
    gender = db.Column(db.String(10))
    address = db.Column(db.Text)
    emergency_contact = db.Column(db.String(20))
    emergency_name = db.Column(db.String(100))
    medical_aid = db.Column(db.String(50))
    medical_aid_number = db.Column(db.String(50))
    language_preference = db.Column(db.String(20), default='english')
    allergies = db.Column(db.Text)
    chronic_conditions = db.Column(db.Text)
    blood_type = db.Column(db.String(5))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    visits = db.relationship('PatientVisit', backref='patient', lazy=True)
    appointments = db.relationship('Appointment', backref='patient', lazy=True)

class PatientVisit(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'), nullable=False)
    visit_date = db.Column(db.DateTime, default=datetime.utcnow)
    visit_type = db.Column(db.String(20))
    chief_complaint = db.Column(db.Text)
    symptoms = db.Column(db.Text)
    diagnosis = db.Column(db.Text)
    treatment = db.Column(db.Text)
    medication_prescribed = db.Column(db.Text)
    doctor_notes = db.Column(db.Text)
    nurse_notes = db.Column(db.Text)
    vital_signs = db.Column(db.Text)
    procedures = db.Column(db.Text)
    follow_up_required = db.Column(db.Boolean, default=False)
    follow_up_date = db.Column(db.Date)
    follow_up_notes = db.Column(db.Text)
    status = db.Column(db.String(20), default='completed')
    assigned_doctor = db.Column(db.String(100))
    assigned_nurse = db.Column(db.String(100))

class Appointment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'), nullable=False)
    appointment_date = db.Column(db.Date, nullable=False)
    appointment_time = db.Column(db.String(10), nullable=False)
    purpose = db.Column(db.Text)
    notes = db.Column(db.Text)
    status = db.Column(db.String(20), default='scheduled')
    source = db.Column(db.String(20), default='whatsapp')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class MedicalHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'), nullable=False)
    condition = db.Column(db.String(100), nullable=False)
    diagnosis_date = db.Column(db.Date)
    treatment = db.Column(db.Text)
    status = db.Column(db.String(20))
    notes = db.Column(db.Text)

# WhatsApp Configuration (for future integration)
WHATSAPP_CONFIG = {
    'enabled': False,  # Set to True when ready
    'webhook_url': '/whatsapp_webhook'
}

# Clinic Configuration
CLINIC_HOURS = {
    "Monday": ["08:00", "09:00", "10:00", "11:00", "13:00", "14:00", "15:00"],
    "Tuesday": ["08:00", "09:00", "10:00", "11:00", "13:00", "14:00", "15:00"],
    "Wednesday": ["08:00", "09:00", "10:00", "11:00", "13:00", "14:00", "15:00"],
    "Thursday": ["08:00", "09:00", "10:00", "11:00", "13:00", "14:00", "15:00"],
    "Friday": ["08:00", "09:00", "10:00", "11:00", "13:00", "14:00", "15:00"],
    "Saturday": ["08:00", "09:00", "10:00", "11:00", "13:00"],
}

# Initialize database
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def init_db():
    with app.app_context():
        db.create_all()
        # Create default admin user if not exists
        if not User.query.filter_by(username='admin').first():
            admin = User(
                username='admin',
                email='admin@metawell.ai',
                password_hash=generate_password_hash('admin123'),
                role='admin',
                full_name='System Administrator'
            )
            db.session.add(admin)
            
            # Create sample receptionist
            receptionist = User(
                username='reception',
                email='reception@metawell.ai',
                password_hash=generate_password_hash('reception123'),
                role='receptionist',
                full_name='Reception Staff'
            )
            db.session.add(receptionist)
            db.session.commit()
            print("Default users created: admin/admin123, reception/reception123")

# Routes
@app.route('/')
def home():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
        
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password_hash, password) and user.is_active:
            login_user(user)
            flash(f'Welcome back, {user.full_name}!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password', 'error')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out successfully', 'info')
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    today = datetime.today().date()
    
    # Dashboard statistics
    stats = {
        'total_patients': Patient.query.count(),
        'today_appointments': Appointment.query.filter(
            Appointment.appointment_date == today,
            Appointment.status.in_(['scheduled', 'confirmed'])
        ).count(),
        'today_visits': PatientVisit.query.filter(
            db.func.date(PatientVisit.visit_date) == today
        ).count(),
        'pending_followups': PatientVisit.query.filter(
            PatientVisit.follow_up_required == True,
            PatientVisit.follow_up_date >= today
        ).count(),
        'patients_waiting': Appointment.query.filter(
            Appointment.appointment_date == today,
            Appointment.status == 'arrived'
        ).count()
    }
    
    # Today's appointments
    todays_appointments = Appointment.query.filter(
        Appointment.appointment_date == today
    ).order_by(Appointment.appointment_time).all()
    
    # Recent patients
    recent_patients = Patient.query.order_by(Patient.created_at.desc()).limit(5).all()
    
    # Urgent follow-ups
    urgent_followups = PatientVisit.query.filter(
        PatientVisit.follow_up_required == True,
        PatientVisit.follow_up_date.between(today, today + timedelta(days=3))
    ).limit(5).all()
    
    return render_template('dashboard.html', 
                         stats=stats,
                         todays_appointments=todays_appointments,
                         recent_patients=recent_patients,
                         urgent_followups=urgent_followups,
                         today=today)

# Patient Management
@app.route('/patients')
@login_required
def patients():
    search = request.args.get('search', '')
    page = request.args.get('page', 1, type=int)
    
    if search:
        patients = Patient.query.filter(
            (Patient.first_name.contains(search)) |
            (Patient.last_name.contains(search)) |
            (Patient.patient_id.contains(search)) |
            (Patient.id_number.contains(search)) |
            (Patient.phone_number.contains(search))
        ).order_by(Patient.last_name).paginate(page=page, per_page=20, error_out=False)
    else:
        patients = Patient.query.order_by(Patient.last_name).paginate(page=page, per_page=20, error_out=False)
    
    return render_template('patients.html', patients=patients, search=search)

@app.route('/patient/<int:patient_id>')
@login_required
def patient_detail(patient_id):
    patient = Patient.query.get_or_404(patient_id)
    visits = PatientVisit.query.filter_by(patient_id=patient_id).order_by(PatientVisit.visit_date.desc()).all()
    appointments = Appointment.query.filter_by(patient_id=patient_id).order_by(Appointment.appointment_date.desc()).limit(10).all()
    medical_history = MedicalHistory.query.filter_by(patient_id=patient_id).all()
    
    return render_template('patient_detail.html', 
                         patient=patient, 
                         visits=visits, 
                         appointments=appointments,
                         medical_history=medical_history)

@app.route('/add_patient', methods=['GET', 'POST'])
@login_required
def add_patient():
    if request.method == 'POST':
        try:
            # Generate patient ID
            year = datetime.now().year
            last_patient = Patient.query.order_by(Patient.id.desc()).first()
            new_id = f"MW{year}{str(last_patient.id + 1 if last_patient else 1).zfill(4)}"
            
            patient = Patient(
                patient_id=new_id,
                phone_number=request.form.get('phone_number'),
                first_name=request.form.get('first_name'),
                last_name=request.form.get('last_name'),
                id_number=request.form.get('id_number'),
                date_of_birth=datetime.strptime(request.form.get('date_of_birth'), '%Y-%m-%d') if request.form.get('date_of_birth') else None,
                gender=request.form.get('gender'),
                address=request.form.get('address'),
                emergency_contact=request.form.get('emergency_contact'),
                emergency_name=request.form.get('emergency_name'),
                medical_aid=request.form.get('medical_aid'),
                medical_aid_number=request.form.get('medical_aid_number'),
                allergies=request.form.get('allergies'),
                chronic_conditions=request.form.get('chronic_conditions'),
                blood_type=request.form.get('blood_type')
            )
            
            db.session.add(patient)
            db.session.commit()
            flash('Patient registered successfully!', 'success')
            return redirect(url_for('patient_detail', patient_id=patient.id))
            
        except Exception as e:
            db.session.rollback()
            flash('Error registering patient. Please check the data and try again.', 'error')
    
    return render_template('add_patient.html')

@app.route('/quick_checkin/<int:patient_id>')
@login_required
def quick_checkin(patient_id):
    patient = Patient.query.get_or_404(patient_id)
    
    # Create a new visit record
    visit = PatientVisit(
        patient_id=patient_id,
        visit_type='appointment',
        visit_date=datetime.utcnow(),
        status='in-progress'
    )
    
    db.session.add(visit)
    
    # Update appointment status if exists
    appointment = Appointment.query.filter_by(
        patient_id=patient_id,
        appointment_date=datetime.today().date(),
        status='confirmed'
    ).first()
    
    if appointment:
        appointment.status = 'arrived'
    
    db.session.commit()
    flash(f'{patient.first_name} {patient.last_name} checked in successfully', 'success')
    return redirect(url_for('dashboard'))

# Appointment Management
@app.route('/appointments')
@login_required
def appointments():
    date_str = request.args.get('date', datetime.today().strftime('%Y-%m-%d'))
    selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    
    appointments = Appointment.query.filter(
        Appointment.appointment_date == selected_date
    ).order_by(Appointment.appointment_time).all()
    
    return render_template('appointments.html', 
                         appointments=appointments, 
                         selected_date=selected_date)

@app.route('/confirm_appointment/<int:appointment_id>')
@login_required
def confirm_appointment(appointment_id):
    appointment = Appointment.query.get_or_404(appointment_id)
    appointment.status = 'confirmed'
    db.session.commit()
    flash('Appointment confirmed successfully', 'success')
    return redirect(url_for('appointments'))

# API Endpoints
@app.route('/api/patient_search')
@login_required
def api_patient_search():
    query = request.args.get('q', '')
    patients = Patient.query.filter(
        (Patient.first_name.contains(query)) |
        (Patient.last_name.contains(query)) |
        (Patient.patient_id.contains(query)) |
        (Patient.id_number.contains(query)) |
        (Patient.phone_number.contains(query))
    ).limit(10).all()
    
    results = [{
        'id': p.id,
        'text': f"{p.patient_id} - {p.first_name} {p.last_name} | ID: {p.id_number}"
    } for p in patients]
    
    return jsonify({'results': results})

@app.route('/api/dashboard_stats')
@login_required
def api_dashboard_stats():
    today = datetime.today().date()
    
    stats = {
        'total_patients': Patient.query.count(),
        'today_appointments': Appointment.query.filter(
            Appointment.appointment_date == today,
            Appointment.status.in_(['scheduled', 'confirmed'])
        ).count(),
        'today_visits': PatientVisit.query.filter(
            db.func.date(PatientVisit.visit_date) == today
        ).count(),
        'patients_waiting': Appointment.query.filter(
            Appointment.appointment_date == today,
            Appointment.status == 'arrived'
        ).count()
    }
    
    return jsonify(stats)

# WhatsApp Integration (Basic endpoint for future use)
@app.route('/whatsapp_webhook', methods=['GET', 'POST'])
def whatsapp_webhook():
    if request.method == 'GET':
        # Webhook verification
        verify_token = request.args.get('hub.verify_token')
        challenge = request.args.get('hub.challenge')
        
        if verify_token == os.environ.get('WHATSAPP_VERIFY_TOKEN', 'metawell_ai_2024'):
            return challenge
        return 'Verification failed', 403
    
    elif request.method == 'POST':
        # Process incoming WhatsApp messages
        try:
            data = request.get_json()
            print("WhatsApp webhook received:", data)
            return jsonify({'status': 'received'}), 200
        except Exception as e:
            print("WhatsApp webhook error:", e)
            return jsonify({'status': 'error'}), 500

# Health check endpoint
@app.route('/health')
def health_check():
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'database': 'connected',
        'patients_count': Patient.query.count(),
        'users_count': User.query.count()
    })

# Error handlers
@app.errorhandler(404)
def not_found_error(error):
    return render_template('error.html', message='Page not found'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('error.html', message='Internal server error'), 500

# Initialize the application
if __name__ == '__main__':
    init_db()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=os.environ.get('DEBUG', False))
