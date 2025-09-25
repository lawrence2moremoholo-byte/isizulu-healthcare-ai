# app.py
import os
import json
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import func
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key')

# Database configuration
if os.getenv('DATABASE_URL'):
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL').replace('postgres://', 'postgresql://')
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///clinic.db'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Database Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='receptionist')
    full_name = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Patient(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.String(20), unique=True, nullable=False)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    phone_number = db.Column(db.String(20), nullable=False)
    email = db.Column(db.String(120))
    id_number = db.Column(db.String(20))
    date_of_birth = db.Column(db.Date)
    gender = db.Column(db.String(10))
    address = db.Column(db.Text)
    emergency_contact = db.Column(db.String(100))
    emergency_name = db.Column(db.String(100))
    medical_aid = db.Column(db.String(100))
    medical_aid_number = db.Column(db.String(50))
    language_preference = db.Column(db.String(20), default='english')
    allergies = db.Column(db.Text)
    chronic_conditions = db.Column(db.Text)
    blood_type = db.Column(db.String(5))
    source = db.Column(db.String(20), default='manual')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    appointments = db.relationship('Appointment', backref='patient', lazy=True)
    visits = db.relationship('PatientVisit', backref='patient', lazy=True)
    medical_history = db.relationship('MedicalHistory', backref='patient', lazy=True)

class Appointment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'), nullable=False)
    appointment_date = db.Column(db.Date, nullable=False)
    appointment_time = db.Column(db.String(10), nullable=False)
    status = db.Column(db.String(20), default='scheduled')
    reason = db.Column(db.Text)
    notes = db.Column(db.Text)
    language = db.Column(db.String(20), default='english')
    source = db.Column(db.String(20), default='manual')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class PatientVisit(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'), nullable=False)
    visit_date = db.Column(db.DateTime, default=datetime.utcnow)
    symptoms = db.Column(db.Text)
    diagnosis = db.Column(db.Text)
    treatment = db.Column(db.Text)
    prescription = db.Column(db.Text)
    notes = db.Column(db.Text)
    doctor = db.Column(db.String(100))
    next_appointment = db.Column(db.Date)

class MedicalHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'), nullable=False)
    condition = db.Column(db.String(200), nullable=False)
    diagnosis_date = db.Column(db.Date)
    treatment = db.Column(db.Text)
    notes = db.Column(db.Text)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Language support
LANGUAGES = {
    'english': {'name': 'English', 'greeting': 'Hello'},
    'zulu': {'name': 'isiZulu', 'greeting': 'Sawubona'},
    'afrikaans': {'name': 'Afrikaans', 'greeting': 'Hallo'},
    'xhosa': {'name': 'isiXhosa', 'greeting': 'Molo'},
    'sotho': {'name': 'Sesotho', 'greeting': 'Lumela'},
    'tswana': {'name': 'Setswana', 'greeting': 'Dumela'},
    'tsonga': {'name': 'Xitsonga', 'greeting': 'Avuxeni'},
    'swati': {'name': 'siSwati', 'greeting': 'Sawubona'},
    'venda': {'name': 'Tshivenda', 'greeting': 'Ndaa'},
    'ndebele': {'name': 'isiNdebele', 'greeting': 'Lotjhani'},
    'pedi': {'name': 'Sepedi', 'greeting': 'Dumela'}
}

# Initialize database function
def init_db():
    """Initialize the database with required tables and default data"""
    try:
        with app.app_context():
            # Create all tables
            db.create_all()
            logger.info("Database tables created successfully")
            
            # Create default admin user if not exists
            if not User.query.filter_by(username='admin').first():
                admin = User(
                    username='admin', 
                    role='admin',
                    full_name='System Administrator'
                )
                admin.set_password('admin123')
                db.session.add(admin)
                logger.info("Default admin user created")
            
            # Create default reception user if not exists
            if not User.query.filter_by(username='reception').first():
                reception = User(
                    username='reception', 
                    role='receptionist',
                    full_name='Reception Staff'
                )
                reception.set_password('reception123')
                db.session.add(reception)
                logger.info("Default reception user created")
            
            db.session.commit()
            logger.info("Database initialized successfully!")
            
    except Exception as e:
        logger.error(f"Error initializing database: {str(e)}")
        raise

# Initialize database immediately when app starts
init_db()

# Routes
@app.route('/')
def index():
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
        
        if user and user.check_password(password):
            login_user(user)
            flash('Login successful!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page or url_for('dashboard'))
        else:
            flash('Invalid username or password', 'error')
    
    return render_template('login.html')

@app.route('/dashboard')
@login_required
def dashboard():
    # Dashboard statistics
    total_patients = Patient.query.count()
    today_appointments = Appointment.query.filter(
        Appointment.appointment_date == datetime.today().date()
    ).count()
    upcoming_appointments = Appointment.query.filter(
        Appointment.appointment_date >= datetime.today().date(),
        Appointment.status.in_(['scheduled', 'confirmed'])
    ).count()
    
    # Recent appointments
    recent_appointments = Appointment.query.filter(
        Appointment.appointment_date >= datetime.today().date()
    ).order_by(Appointment.appointment_date.asc()).limit(10).all()
    
    # Language usage statistics
    language_stats = db.session.query(
        Appointment.language, 
        func.count(Appointment.id)
    ).group_by(Appointment.language).all()
    
    return render_template('dashboard.html',
                         total_patients=total_patients,
                         today_appointments=today_appointments,
                         upcoming_appointments=upcoming_appointments,
                         recent_appointments=recent_appointments,
                         language_stats=language_stats)
    
@app.route('/add_appointment', methods=['GET', 'POST'])
@login_required
def add_appointment():
    if request.method == 'POST':
        try:
            appointment = Appointment(
                patient_id=request.form.get('patient_id'),
                appointment_date=datetime.strptime(request.form.get('appointment_date'), '%Y-%m-%d').date(),
                appointment_time=request.form.get('appointment_time'),
                reason=request.form.get('reason'),
                notes=request.form.get('notes'),
                language=request.form.get('language', 'english')
            )
            
            db.session.add(appointment)
            db.session.commit()
            flash('Appointment scheduled successfully!', 'success')
            return redirect(url_for('appointments'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error scheduling appointment: {str(e)}', 'error')
    
    patients = Patient.query.order_by(Patient.first_name, Patient.last_name).all()
    return render_template('add_appointment.html', patients=patients, datetime=datetime)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out successfully.', 'success')
    return redirect(url_for('login'))

@app.route('/patients')
@login_required
def patients():
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    
    query = Patient.query
    
    if search:
        query = query.filter(
            (Patient.first_name.ilike(f'%{search}%')) |
            (Patient.last_name.ilike(f'%{search}%')) |
            (Patient.patient_id.ilike(f'%{search}%')) |
            (Patient.phone_number.ilike(f'%{search}%'))
        )
    
    patients = query.order_by(Patient.created_at.desc()).paginate(
        page=page, per_page=10, error_out=False
    )
    
    return render_template('patients.html', patients=patients, search=search)

@app.route('/patient/<int:patient_id>')
@login_required
def patient_detail(patient_id):
    patient = Patient.query.get_or_404(patient_id)
    appointments = Appointment.query.filter_by(patient_id=patient_id).order_by(Appointment.appointment_date.desc()).all()
    visits = PatientVisit.query.filter_by(patient_id=patient_id).order_by(PatientVisit.visit_date.desc()).all()
    medical_history = MedicalHistory.query.filter_by(patient_id=patient_id).all()
    
    return render_template('patient_detail.html', 
                         patient=patient, 
                         appointments=appointments,
                         visits=visits,
                         medical_history=medical_history)

@app.route('/add_patient', methods=['GET', 'POST'])
@login_required
def add_patient():
    if request.method == 'POST':
        try:
            # Generate patient ID
            year = datetime.now().year
            last_patient = Patient.query.order_by(Patient.id.desc()).first()
            last_id = last_patient.id if last_patient else 0
            new_id = f"MW{year}{str(last_id + 1).zfill(4)}"
            
            patient = Patient(
                patient_id=new_id,
                first_name=request.form.get('first_name'),
                last_name=request.form.get('last_name'),
                phone_number=request.form.get('phone_number'),
                email=request.form.get('email'),
                id_number=request.form.get('id_number'),
                date_of_birth=datetime.strptime(request.form.get('date_of_birth'), '%Y-%m-%d') if request.form.get('date_of_birth') else None,
                gender=request.form.get('gender'),
                address=request.form.get('address'),
                emergency_contact=request.form.get('emergency_contact'),
                emergency_name=request.form.get('emergency_name'),
                medical_aid=request.form.get('medical_aid'),
                medical_aid_number=request.form.get('medical_aid_number'),
                language_preference=request.form.get('language_preference', 'english'),
                allergies=request.form.get('allergies'),
                chronic_conditions=request.form.get('chronic_conditions'),
                blood_type=request.form.get('blood_type'),
                source='manual'
            )
            
            db.session.add(patient)
            db.session.commit()
            flash('Patient added successfully!', 'success')
            return redirect(url_for('patient_detail', patient_id=patient.id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding patient: {str(e)}', 'error')
    
    return render_template('add_patient.html')

@app.route('/appointments')
@login_required
def appointments():
    page = request.args.get('page', 1, type=int)
    date_filter = request.args.get('date', '')
    status_filter = request.args.get('status', '')
    
    query = Appointment.query
    
    if date_filter:
        try:
            filter_date = datetime.strptime(date_filter, '%Y-%m-%d').date()
            query = query.filter(Appointment.appointment_date == filter_date)
        except ValueError:
            pass
    
    if status_filter:
        query = query.filter(Appointment.status == status_filter)
    
    appointments = query.order_by(Appointment.appointment_date.asc(), Appointment.appointment_time.asc()).paginate(
        page=page, per_page=15, error_out=False
    )
    
    return render_template('appointments.html', 
                         appointments=appointments,
                         date_filter=date_filter,
                         status_filter=status_filter)

@app.route('/add_appointment', methods=['GET', 'POST'])
@login_required
def add_appointment():
    if request.method == 'POST':
        try:
            appointment = Appointment(
                patient_id=request.form.get('patient_id'),
                appointment_date=datetime.strptime(request.form.get('appointment_date'), '%Y-%m-%d').date(),
                appointment_time=request.form.get('appointment_time'),
                reason=request.form.get('reason'),
                notes=request.form.get('notes'),
                language=request.form.get('language', 'english')
            )
            
            db.session.add(appointment)
            db.session.commit()
            flash('Appointment scheduled successfully!', 'success')
            return redirect(url_for('appointments'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error scheduling appointment: {str(e)}', 'error')
    
    patients = Patient.query.all()
    return render_template('add_appointment.html', patients=patients)

# WhatsApp webhook endpoint
@app.route('/whatsapp', methods=['POST'])
def whatsapp_webhook():
    try:
        # Basic WhatsApp webhook implementation
        incoming_msg = request.values.get('Body', '').strip()
        from_number = request.values.get('From', '').replace('whatsapp:', '')
        
        logger.info(f"WhatsApp message from {from_number}: {incoming_msg}")
        
        # Placeholder response
        response = "Thank you for your message. Our clinic will respond shortly."
        
        return f'<Response><Message>{response}</Message></Response>'
        
    except Exception as e:
        logger.error(f"WhatsApp webhook error: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

# API endpoints for statistics
@app.route('/api/stats')
@login_required
def api_stats():
    stats = {
        'total_patients': Patient.query.count(),
        'today_appointments': Appointment.query.filter(
            Appointment.appointment_date == datetime.today().date()
        ).count(),
        'whatsapp_bookings': Appointment.query.filter_by(source='whatsapp').count(),
        'languages_used': db.session.query(Appointment.language).distinct().count()
    }
    return jsonify(stats)

# Add error handlers
@app.errorhandler(404)
def not_found_error(error):
    return render_template('error.html', error=error), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('error.html', error=error), 500

# Application entry point
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=os.getenv('FLASK_DEBUG', 'False').lower() == 'true')
