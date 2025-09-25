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

# WhatsApp Configuration
CLINIC_HOURS = {
    "start": "06:00",  # 6 AM
    "end": "21:00",    # 9 PM
    "days": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
}

# WhatsApp conversation states (in-memory storage)
whatsapp_conversations = {}

# Multilingual Responses Configuration
WHATSAPP_RESPONSES = {
    'english': {
        'welcome': "🏥 *MetaWell AI Clinic*\n\nPlease choose your language:\n\n1. English\n2. isiZulu\n3. Afrikaans\n4. isiXhosa\n\n*Reply with the number* of your preferred language",
        'greeting': "Hello! 👋 Thank you for contacting MetaWell AI Clinic. Would you like to book a medical appointment? (Reply *YES* or *NO*)",
        'show_days': "📅 *Available Appointment Days:*\n\n{days}\n\nWhich day would you prefer? (Reply with the day name)",
        'choose_day': "Great! You chose *{day}*. Checking available time slots...",
        'show_slots': "⏰ *Available Times on {day}:*\n\n{slots}\n\nPlease reply with your preferred time (e.g., 09:00)",
        'booking_success': "✅ *Appointment Confirmed!*\n\n📅 Date: {day}\n⏰ Time: {time}\n📍 Clinic: MetaWell AI Clinic\n📋 Purpose: General Consultation\n\nPlease arrive 15 minutes early with your ID document. We look forward to seeing you!",
        'emergency_advice': "🚨 *Emergency Notice:*\n\nIf this is a medical emergency, please:\n• Visit your nearest hospital immediately\n• Call 10111 for ambulance\n• Go to the emergency room\n\n*Your safety is our priority!*",
        'after_hours': "🏥 *MetaWell AI Clinic - After Hours*\n\nThank you for your message! Our clinic is currently closed.\n\n*Clinic Hours:*\n🕘 Monday-Friday: 6:00 AM - 9:00 PM\n🕘 Saturday: 8:00 AM - 5:00 PM\n❌ Sunday: Closed\n\nWe'll respond to your message during our next business hours.",
        'goodbye': "Thank you for contacting MetaWell AI Clinic! Stay healthy! 🌟",
        'invalid_choice': "❌ I didn't understand that. Please try again with a valid option.",
        'yes': ['yes', 'y', 'yeah', 'yebo', 'ya'],
        'no': ['no', 'n', 'nah', 'cha']
    },
    'zulu': {
        'welcome': "🏥 *MetaWell AI Clinic*\n\nSicela ukhethe ulimi:\n\n1. isiZulu\n2. English\n3. Afrikaans\n4. isiXhosa\n\n*Phendula ngenombolo* yolimi oluthandayo",
        'greeting': "Sawubona! 👋 Ngiyabonga ukuxhumana ne-MetaWell AI Clinic. Ingabe ufuna ukubhuka isikhathi sokwelapha? (Phendula *YEBO* noma *CHA*)",
        'show_days': "📅 *Izinsuku Ezitholakalayo:*\n\n{days}\n\nUfuna usuku luni? (Phendula ngeligama lousuku)",
        'choose_day': "Kuhle! Ukhethe u-*{day}*. Ngibheka izikhathi ezitholakalayo...",
        'show_slots': "⏰ *Izikhathi ku-{day}:*\n\n{slots}\n\nSicela uphendule ngesikhathi osithandayo (isib. 09:00)",
        'booking_success': "✅ *Isikhathi Siqinisekisiwe!*\n\n📅 Usuku: {day}\n⏰ Isikhathi: {time}\n📍 Isibhedlela: MetaWell AI Clinic\n📋 Inhloso: Ukuxilongwa Okujwayelekile\n\nSicela ufike imizuzu engu-15 ngaphambi kwesikhathi. Siyakulindile!",
        'goodbye': "Ngiyabonga ukuxhumana ne-MetaWell AI Clinic! Sala uphile! 🌟",
        'yes': ['yebo', 'y', 'ya'],
        'no': ['cha', 'c', 'hayi']
    },
    'afrikaans': {
        'welcome': "🏥 *MetaWell AI Clinic*\n\nKies asseblief jou taal:\n\n1. Afrikaans\n2. English\n3. isiZulu\n4. isiXhosa\n\n*Antwoord met die nommer* van jou voorkeurtaal",
        'greeting': "Hallo! 👋 Dankie dat jy MetaWell AI Clinic gekontak het. Wil jy 'n afspraak maak? (Antwoord *JA* of *NEE*)",
        'show_days': "📅 *Beskikbare Afspraakdae:*\n\n{days}\n\nWatter dag verkies jy? (Antwoord met die dag naam)",
        'booking_success': "✅ *Afspraak Bevestig!*\n\n📅 Datum: {day}\n⏰ Tyd: {time}\n📍 Kliniek: MetaWell AI Clinic\n\nWees asseblief 15 minute vroeg met jou ID-dokument.",
        'goodbye': "Dankie vir die kontak! Bly gesond! 🌟",
        'yes': ['ja', 'j', 'y'],
        'no': ['nee', 'n', 'ne']
    }
}

def is_within_business_hours():
    """Check if current time is within clinic hours"""
    now = datetime.now()
    current_time = now.time()
    
    # Parse clinic hours
    start_time = datetime.strptime(CLINIC_HOURS["start"], "%H:%M").time()
    end_time = datetime.strptime(CLINIC_HOURS["end"], "%H:%M").time()
    
    # Check if current day is a clinic day
    current_day = now.strftime("%A")
    if current_day not in CLINIC_HOURS["days"]:
        return False
    
    return start_time <= current_time <= end_time

def get_available_days(language='english'):
    """Get available appointment days (next 7 days excluding Sundays)"""
    today = datetime.now()
    available_days = []
    
    for i in range(1, 8):  # Next 7 days
        future_date = today + timedelta(days=i)
        day_name = future_date.strftime("%A")
        
        # Skip Sundays and non-clinic days
        if day_name == "Sunday" or day_name not in CLINIC_HOURS["days"]:
            continue
            
        # Check if we haven't reached maximum appointments for the day
        appointments_count = Appointment.query.filter(
            Appointment.appointment_date == future_date.date(),
            Appointment.status.in_(['scheduled', 'confirmed'])
        ).count()
        
        if appointments_count < 20:  # Max 20 appointments per day
            # Translate day name based on language
            day_translation = day_name  # Default to English
            if language == 'zulu':
                zulu_days = {'Monday': 'Msombuluko', 'Tuesday': 'Lwesibili', 'Wednesday': 'Lwesithathu', 
                            'Thursday': 'Lwesine', 'Friday': 'Lwesihlanu', 'Saturday': 'Mgqibelo'}
                day_translation = zulu_days.get(day_name, day_name)
            elif language == 'afrikaans':
                afrikaans_days = {'Monday': 'Maandag', 'Tuesday': 'Dinsdag', 'Wednesday': 'Woensdag',
                                 'Thursday': 'Donderdag', 'Friday': 'Vrydag', 'Saturday': 'Saterdag'}
                day_translation = afrikaans_days.get(day_name, day_name)
                
            available_days.append(day_translation)
    
    return available_days

def get_available_slots(day, language='english'):
    """Get available time slots for a specific day"""
    # Map day names back to English for processing
    day_mapping = {
        'zulu': {'Msombuluko': 'Monday', 'Lwesibili': 'Tuesday', 'Lwesithathu': 'Wednesday',
                'Lwesine': 'Thursday', 'Lwesihlanu': 'Friday', 'Mgqibelo': 'Saturday'},
        'afrikaans': {'Maandag': 'Monday', 'Dinsdag': 'Tuesday', 'Woensdag': 'Wednesday',
                     'Donderdag': 'Thursday', 'Vrydag': 'Friday', 'Saterdag': 'Saturday'}
    }
    
    day_english = day
    for lang, days_map in day_mapping.items():
        if day in days_map:
            day_english = days_map[day]
            break
    
    # Standard time slots
    all_slots = ["08:00", "09:00", "10:00", "11:00", "12:00", "13:00", "14:00", "15:00", "16:00"]
    
    # Find the actual date for the selected day
    today = datetime.now()
    for i in range(1, 8):
        future_date = today + timedelta(days=i)
        if future_date.strftime("%A") == day_english:
            target_date = future_date.date()
            break
    else:
        return []
    
    # Get booked slots for that day
    booked_slots = [appt.appointment_time for appt in Appointment.query.filter(
        Appointment.appointment_date == target_date,
        Appointment.status.in_(['scheduled', 'confirmed'])
    ).all()]
    
    # Return available slots
    return [slot for slot in all_slots if slot not in booked_slots]

def create_patient_from_whatsapp(phone_number, language='english'):
    """Create or find patient from WhatsApp booking"""
    patient = Patient.query.filter_by(phone_number=phone_number).first()
    
    if not patient:
        # Generate patient ID
        year = datetime.now().year
        last_patient = Patient.query.order_by(Patient.id.desc()).first()
        last_id = last_patient.id if last_patient else 0
        new_id = f"MW{year}{str(last_id + 1).zfill(4)}"
        
        patient = Patient(
            patient_id=new_id,
            phone_number=phone_number,
            first_name="WhatsApp",
            last_name="Patient",
            language_preference=language,
            source='whatsapp'
        )
        db.session.add(patient)
        db.session.commit()
    
    return patient

def create_appointment_from_whatsapp(patient_id, day, time, language='english'):
    """Create appointment from WhatsApp booking"""
    # Map day back to English
    day_mapping = {
        'zulu': {'Msombuluko': 'Monday', 'Lwesibili': 'Tuesday', 'Lwesithathu': 'Wednesday',
                'Lwesine': 'Thursday', 'Lwesihlanu': 'Friday', 'Mgqibelo': 'Saturday'},
        'afrikaans': {'Maandag': 'Monday', 'Dinsdag': 'Tuesday', 'Woensdag': 'Wednesday',
                     'Donderdag': 'Thursday', 'Vrydag': 'Friday', 'Saterdag': 'Saturday'}
    }
    
    day_english = day
    for lang, days_map in day_mapping.items():
        if day in days_map:
            day_english = days_map[day]
            break
    
    # Find the actual date
    today = datetime.now()
    for i in range(1, 8):
        future_date = today + timedelta(days=i)
        if future_date.strftime("%A") == day_english:
            appointment_date = future_date.date()
            break
    else:
        appointment_date = today.date() + timedelta(days=1)
    
    appointment = Appointment(
        patient_id=patient_id,
        appointment_date=appointment_date,
        appointment_time=time,
        purpose="Booking via WhatsApp",
        status='scheduled',
        source='whatsapp',
        language=language
    )
    
    db.session.add(appointment)
    db.session.commit()
    return appointment

def handle_language_selection(message, state_data, phone_number):
    """Handle language selection step"""
    language_choices = {
        '1': 'english', 'english': 'english',
        '2': 'zulu', 'zulu': 'zulu', 'isizulu': 'zulu',
        '3': 'afrikaans', 'afrikaans': 'afrikaans',
        '4': 'xhosa', 'xhosa': 'xhosa', 'isixhosa': 'xhosa'
    }
    
    if message.lower() in language_choices:
        state_data['language'] = language_choices[message.lower()]
        state_data['state'] = 'GREETING'
        return WHATSAPP_RESPONSES[state_data['language']]['greeting']
    else:
        # Default to English
        state_data['language'] = 'english'
        state_data['state'] = 'GREETING'
        return WHATSAPP_RESPONSES['english']['greeting']

def handle_greeting(message, state_data, phone_number):
    """Handle initial greeting and appointment intent"""
    lang_config = WHATSAPP_RESPONSES[state_data['language']]
    
    if any(word in message.lower() for word in lang_config['yes']):
        state_data['state'] = 'DAY_SELECTION'
        available_days = get_available_days(state_data['language'])
        days_text = "\n".join([f"• {day}" for day in available_days])
        return lang_config['show_days'].format(days=days_text)
    elif any(word in message.lower() for word in lang_config['no']):
        if phone_number in whatsapp_conversations:
            del whatsapp_conversations[phone_number]
        return lang_config['goodbye']
    else:
        return lang_config['invalid_choice']

def handle_day_selection(message, state_data, phone_number):
    """Handle day selection step"""
    lang_config = WHATSAPP_RESPONSES[state_data['language']]
    available_days = get_available_days(state_data['language'])
    
    # Check if message matches any available day
    selected_day = None
    for day in available_days:
        if day.lower() in message.lower():
            selected_day = day
            break
    
    if selected_day:
        state_data['booking_data']['day'] = selected_day
        state_data['state'] = 'TIME_SELECTION'
        return lang_config['choose_day'].format(day=selected_day)
    else:
        days_text = "\n".join([f"• {day}" for day in available_days])
        return lang_config['show_days'].format(days=days_text)

def handle_time_selection(message, state_data, phone_number):
    """Handle time selection step"""
    lang_config = WHATSAPP_RESPONSES[state_data['language']]
    selected_day = state_data['booking_data'].get('day')
    
    if not selected_day:
        state_data['state'] = 'DAY_SELECTION'
        available_days = get_available_days(state_data['language'])
        days_text = "\n".join([f"• {day}" for day in available_days])
        return lang_config['show_days'].format(days=days_text)
    
    available_slots = get_available_slots(selected_day, state_data['language'])
    
    # Check if message matches any available time slot
    selected_time = None
    for slot in available_slots:
        if slot in message or slot.replace(':00', '') in message:
            selected_time = slot
            break
    
    if selected_time:
        # Create patient and appointment
        patient = create_patient_from_whatsapp(phone_number, state_data['language'])
        appointment = create_appointment_from_whatsapp(
            patient.id, selected_day, selected_time, state_data['language']
        )
        
        state_data['patient_id'] = patient.id
        state_data['state'] = 'COMPLETED'
        
        # Clean up conversation after completion
        if phone_number in whatsapp_conversations:
            del whatsapp_conversations[phone_number]
        
        return lang_config['booking_success'].format(
            day=selected_day, 
            time=selected_time
        )
    else:
        slots_text = "\n".join([f"• {slot}" for slot in available_slots])
        return lang_config['show_slots'].format(day=selected_day, slots=slots_text)

def process_whatsapp_message(message, phone_number):
    """Main function to process WhatsApp messages"""
    msg_lower = message.lower().strip()
    
    # Initialize conversation state if new
    if phone_number not in whatsapp_conversations:
        whatsapp_conversations[phone_number] = {
            'state': 'LANGUAGE_SELECTION',
            'language': 'english',
            'patient_id': None,
            'booking_data': {},
            'last_active': datetime.now()
        }
    
    state_data = whatsapp_conversations[phone_number]
    current_state = state_data['state']
    
    # Route to appropriate handler based on current state
    if current_state == 'LANGUAGE_SELECTION':
        return handle_language_selection(msg_lower, state_data, phone_number)
    elif current_state == 'GREETING':
        return handle_greeting(msg_lower, state_data, phone_number)
    elif current_state == 'DAY_SELECTION':
        return handle_day_selection(msg_lower, state_data, phone_number)
    elif current_state == 'TIME_SELECTION':
        return handle_time_selection(msg_lower, state_data, phone_number)
    else:
        return WHATSAPP_RESPONSES[state_data['language']]['invalid_choice']

# Updated WhatsApp Webhook Route (Replace the existing one)
@app.route('/whatsapp', methods=['POST'])
def whatsapp_webhook():
    try:
        incoming_msg = request.values.get('Body', '').strip()
        from_number = request.values.get('From', '').replace('whatsapp:', '')
        
        logger.info(f"WhatsApp message from {from_number}: {incoming_msg}")
        
        # Check if outside business hours
        if not is_within_business_hours():
            if from_number not in whatsapp_conversations:
                # First message outside hours
                current_lang = whatsapp_conversations[from_number]['language'] if from_number in whatsapp_conversations else 'english'
                response = WHATSAPP_RESPONSES[current_lang]['after_hours']
                
                # Still process the message but indicate after-hours
                booking_response = process_whatsapp_message(incoming_msg, from_number)
                return f'<Response><Message>{response}\\n\\n---\\n\\n{booking_response}</Message></Response>'
        
        # Process message normally
        response = process_whatsapp_message(incoming_msg, from_number)
        return f'<Response><Message>{response}</Message></Response>'
        
    except Exception as e:
        logger.error(f"WhatsApp webhook error: {str(e)}")
        # Fallback response
        return '<Response><Message>🚨 System temporarily unavailable. Please try again in a few moments.</Message></Response>'
        
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
    try:
        # Dashboard statistics
        total_patients = Patient.query.count()
        today_appointments = Appointment.query.filter(
            Appointment.appointment_date == datetime.today().date()
        ).count()
        upcoming_appointments = Appointment.query.filter(
            Appointment.appointment_date >= datetime.today().date(),
            Appointment.status.in_(['scheduled', 'confirmed'])
        ).count()
        whatsapp_bookings = Appointment.query.filter_by(source='whatsapp').count()
        today_visits = PatientVisit.query.filter(
            db.func.date(PatientVisit.visit_date) == datetime.today().date()
        ).count()
        
        # Recent appointments
        recent_appointments = Appointment.query.filter(
            Appointment.appointment_date >= datetime.today().date()
        ).order_by(Appointment.appointment_date.asc()).limit(10).all()
        
        # Recent WhatsApp patients
        recent_whatsapp = Patient.query.filter_by(source='whatsapp').order_by(Patient.created_at.desc()).limit(5).all()
        
        # Language usage statistics
        language_stats = db.session.query(
            Appointment.language, 
            func.count(Appointment.id)
        ).group_by(Appointment.language).all()
        
        # Create stats dictionary for template compatibility
        stats = {
            'total_patients': total_patients,
            'today_appointments': today_appointments,
            'upcoming_appointments': upcoming_appointments,
            'whatsapp_bookings': whatsapp_bookings,
            'today_visits': today_visits
        }
        
        return render_template('dashboard.html',
                             stats=stats,
                             todays_appointments=recent_appointments,  # Fixed variable name
                             recent_patients=Patient.query.order_by(Patient.created_at.desc()).limit(5).all(),
                             recent_whatsapp=recent_whatsapp,
                             today=datetime.today().date(),
                             total_patients=total_patients,  # Keep individual variables for backward compatibility
                             today_appointments=today_appointments,
                             upcoming_appointments=upcoming_appointments,
                             language_stats=language_stats)
                             
    except Exception as e:
        logger.error(f"Dashboard error: {str(e)}", exc_info=True)
        flash('Error loading dashboard. Please try again.', 'error')
        return redirect(url_for('index'))

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

@app.route('/edit_patient/<int:patient_id>', methods=['GET', 'POST'])
@login_required
def edit_patient(patient_id):
    patient = Patient.query.get_or_404(patient_id)
    
    if request.method == 'POST':
        try:
            patient.first_name = request.form.get('first_name')
            patient.last_name = request.form.get('last_name')
            patient.phone_number = request.form.get('phone_number')
            patient.email = request.form.get('email')
            patient.id_number = request.form.get('id_number')
            patient.gender = request.form.get('gender')
            patient.address = request.form.get('address')
            patient.emergency_contact = request.form.get('emergency_contact')
            patient.emergency_name = request.form.get('emergency_name')
            patient.medical_aid = request.form.get('medical_aid')
            patient.medical_aid_number = request.form.get('medical_aid_number')
            patient.language_preference = request.form.get('language_preference', 'english')
            patient.allergies = request.form.get('allergies')
            patient.chronic_conditions = request.form.get('chronic_conditions')
            patient.blood_type = request.form.get('blood_type')
            
            # Handle date of birth
            dob = request.form.get('date_of_birth')
            if dob:
                patient.date_of_birth = datetime.strptime(dob, '%Y-%m-%d')
            
            db.session.commit()
            flash('Patient information updated successfully!', 'success')
            return redirect(url_for('patient_detail', patient_id=patient.id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating patient: {str(e)}', 'error')
    
    return render_template('edit_patient.html', patient=patient)

@app.route('/patient/<int:patient_id>/book_appointment', methods=['GET', 'POST'])
@login_required
def book_appointment_for_patient(patient_id):
    patient = Patient.query.get_or_404(patient_id)
    
    if request.method == 'POST':
        try:
            appointment = Appointment(
                patient_id=patient_id,
                appointment_date=datetime.strptime(request.form.get('appointment_date'), '%Y-%m-%d').date(),
                appointment_time=request.form.get('appointment_time'),
                reason=request.form.get('reason'),
                notes=request.form.get('notes'),
                language=request.form.get('language', patient.language_preference)
            )
            
            db.session.add(appointment)
            db.session.commit()
            flash(f'Appointment booked successfully for {patient.first_name} {patient.last_name}!', 'success')
            return redirect(url_for('patient_detail', patient_id=patient_id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error booking appointment: {str(e)}', 'error')
    
    return render_template('book_appointment.html', patient=patient, datetime=datetime)

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
    
    patients = Patient.query.order_by(Patient.first_name, Patient.last_name).all()
    return render_template('add_appointment.html', patients=patients, datetime=datetime)

# Enhanced WhatsApp conversation states
whatsapp_conversations = {}
CLINIC_HOURS = {"start": "06:00", "end": "21:00"}  # 6am to 9pm

@app.route('/whatsapp', methods=['POST'])
def whatsapp_webhook():
    try:
        incoming_msg = request.values.get('Body', '').strip()
        from_number = request.values.get('From', '').replace('whatsapp:', '')
        
        logger.info(f"WhatsApp message from {from_number}: {incoming_msg}")
        
        # Check if outside business hours (9pm to 6am)
        current_time = datetime.now().time()
        start_time = datetime.strptime(CLINIC_HOURS["start"], "%H:%M").time()
        end_time = datetime.strptime(CLINIC_HOURS["end"], "%H:%M").time()
        
        if current_time < start_time or current_time > end_time:
            response = get_outside_hours_response(from_number, incoming_msg)
        else:
            response = process_whatsapp_message(incoming_msg, from_number)
        
        return f'<Response><Message>{response}</Message></Response>'
        
    except Exception as e:
        logger.error(f"WhatsApp webhook error: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

def get_outside_hours_response(phone_number, message):
    """Handle messages outside business hours"""
    if phone_number not in whatsapp_conversations:
        # First message outside hours - provide helpful response
        return """🏥 *MetaWell AI Clinic - After Hours*

Thank you for your message! Our clinic is currently closed.

*Clinic Hours:*
🕘 Monday-Friday: 6:00 AM - 9:00 PM
🕘 Saturday: 8:00 AM - 5:00 PM
❌ Sunday: Closed

We'll respond to your message during our next business hours. For medical emergencies, please visit your nearest hospital or call 10111.

*Your message:* \"{}\"

We look forward to assisting you tomorrow! 🌟""".format(message)
    else:
        # Continue existing conversation with after-hours notice
        response = process_whatsapp_message(message, phone_number)
        return response + "\n\n📋 *Note:* Clinic is currently closed. We'll confirm your booking tomorrow."

def process_whatsapp_message(message, phone_number):
    """Process multilingual WhatsApp booking flow"""
    msg_lower = message.lower().strip()
    
    # Initialize or get conversation state
    if phone_number not in whatsapp_conversations:
        whatsapp_conversations[phone_number] = {
            'state': 'LANGUAGE_SELECTION',
            'language': 'english',
            'patient_id': None,
            'booking_data': {},
            'last_active': datetime.now()
        }
    
    state_data = whatsapp_conversations[phone_number]
    current_state = state_data['state']
    current_language = state_data['language']
    
    # Multilingual responses configuration
    responses = {
        'english': {
            'welcome': "🏥 *MetaWell AI Clinic*\n\nPlease choose your language:\n\n1. English\n2. isiZulu\n3. Afrikaans\n4. isiXhosa\n\n*Reply with the number* of your preferred language",
            'greeting': "Hello! 👋 Thank you for contacting MetaWell AI Clinic. Would you like to book a medical appointment? (Reply *YES* or *NO*)",
            'show_days': "📅 *Available Appointment Days:*\n\n{days}\n\nWhich day would you prefer?",
            'choose_day': "Great! You chose *{day}*. Checking available time slots...",
            'show_slots': "⏰ *Available Times on {day}:*\n\n{slots}\n\nPlease reply with your preferred time (e.g., 09:00)",
            'booking_success': "✅ *Appointment Confirmed!*\n\n📅 Date: {day}\n⏰ Time: {time}\n📍 Clinic: MetaWell AI Clinic\n📋 Purpose: {purpose}\n\nPlease arrive 15 minutes early with your ID document.",
            'emergency_advice': "🚨 *Emergency Notice:*\n\nIf this is a medical emergency, please:\n• Visit your nearest hospital immediately\n• Call 10111 for ambulance\n• Go to the emergency room\n\n*Your safety is our priority!*",
            'goodbye': "Thank you for contacting MetaWell AI Clinic! Stay healthy! 🌟",
            'invalid_choice': "❌ Invalid choice. Please try again."
        },
        'zulu': {
            'welcome': "🏥 *MetaWell AI Clinic*\n\nSicela ukhethe ulimi:\n\n1. isiZulu\n2. English\n3. Afrikaans\n4. isiXhosa\n\n*Phendula ngenombolo* yolimi oluthandayo",
            'greeting': "Sawubona! 👋 Ngiyabonga ukuxhumana ne-MetaWell AI Clinic. Ingabe ufuna ukubhuka isikhathi sokwelapha? (Phendula *YEBO* noma *CHA*)",
            # ... add other language responses
        }
    }
    
    # State machine for conversation flow
    if current_state == 'LANGUAGE_SELECTION':
        return handle_language_selection(msg_lower, state_data, responses)
    elif current_state == 'GREETING':
        return handle_greeting(msg_lower, state_data, responses[current_language])
    elif current_state == 'DAY_SELECTION':
        return handle_day_selection(msg_lower, state_data, responses[current_language])
    elif current_state == 'TIME_SELECTION':
        return handle_time_selection(msg_lower, state_data, responses[current_language])
    elif current_state == 'CONFIRMATION':
        return handle_confirmation(msg_lower, state_data, responses[current_language])
    
    return responses[current_language]['invalid_choice']

def handle_language_selection(message, state_data, responses):
    """Handle language selection step"""
    language_map = {
        '1': 'english', 'english': 'english',
        '2': 'zulu', 'zulu': 'zulu', 
        '3': 'afrikaans', 'afrikaans': 'afrikaans',
        '4': 'xhosa', 'xhosa': 'xhosa'
    }
    
    if message in language_map:
        state_data['language'] = language_map[message]
        state_data['state'] = 'GREETING'
        return responses[state_data['language']]['greeting']
    else:
        # Default to English if not recognized
        state_data['language'] = 'english'
        state_data['state'] = 'GREETING'
        return responses['english']['greeting']

def handle_greeting(message, state_data, responses):
    """Handle initial greeting and appointment intent"""
    if any(word in message for word in ['yes', 'yebo', 'ja', 'y']):
        state_data['state'] = 'DAY_SELECTION'
        available_days = get_available_days(state_data['language'])
        days_text = "\n".join([f"• {day}" for day in available_days])
        return responses['show_days'].format(days=days_text)
    else:
        del whatsapp_conversations[state_data['phone_number']]
        return responses['goodbye']

# Add similar handler functions for day selection, time selection, and confirmation

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
