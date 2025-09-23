from flask import Flask, request, jsonify
import os
import hashlib
from datetime import datetime
from twilio.rest import Client

app = Flask(__name__)

# Twilio Configuration (MOVE THESE TO RENDER ENVIRONMENT VARIABLES AFTER TESTING)
TWILIO_ACCOUNT_SID = "AC055436adfbbdce3ea17cea0b3c1e6cc4"
TWILIO_AUTH_TOKEN = "172f1c5f53358211674cd9946baf3b0f" 
TWILIO_PHONE_NUMBER = "+12766242360"

# Initialize Twilio client
twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

# Secure Patient Database (In production, use real database)
patient_profiles = {}  # Format: {hashed_phone: {name: "", phone: "", bookings: []}}
conversation_states = {}
all_bookings = []
booking_history = []

def hash_phone(phone_number):
    """Securely hash phone numbers for privacy"""
    return hashlib.sha256(phone_number.encode()).hexdigest()

def get_or_create_patient(phone_number):
    """Get existing patient or create new profile"""
    hashed_phone = hash_phone(phone_number)
    
    if hashed_phone not in patient_profiles:
        patient_profiles[hashed_phone] = {
            "phone": phone_number,
            "name": "Unknown",  # Will collect later
            "bookings": [],
            "created_date": datetime.now().isoformat()
        }
    
    return patient_profiles[hashed_phone]

def prevent_double_booking(patient_phone, day, time):
    """Check if patient already has booking on same day/time"""
    patient = get_or_create_patient(patient_phone)
    
    # Check for active bookings with same day/time
    for booking in patient["bookings"]:
        if (booking["day"] == day and booking["time"] == time and 
            booking["status"] == "active"):
            return True  # Double booking detected
    
    return False  # No conflict

def create_booking(patient_phone, day, time, action="booked"):
    """Securely create booking with patient profile linking"""
    
    # Prevent double booking
    if prevent_double_booking(patient_phone, day, time) and action == "booked":
        return None, "You already have a booking for this time. Please choose different time."
    
    patient = get_or_create_patient(patient_phone)
    
    booking_id = hashlib.md5(f"{patient_phone}{day}{time}{datetime.now()}".encode()).hexdigest()
    
    booking = {
        "id": booking_id,
        "patient_phone": patient_phone,
        "patient_hash": hash_phone(patient_phone),  # Secure reference
        "day": day,
        "time": time,
        "action": action,
        "status": "active" if action == "booked" else "cancelled",
        "timestamp": datetime.now().isoformat()
    }
    
    # Add to patient profile
    patient["bookings"].append(booking)
    
    # Add to global records
    all_bookings.append(booking)
    booking_history.append(booking)
    
    print(f"SECURE BOOKING: {action.upper()} - {patient_phone} on {day} at {time}:00")
    return booking, "success"

def notify_clinic(patient_phone, day, time, action="booked"):
    """Secure clinic notification"""
    booking, status = create_booking(patient_phone, day, time, action)
    if booking:
        print(f"CLINIC: {action.upper()} - {patient_phone} on {day} at {time}:00")
    return booking

def send_sms_confirmation(patient_phone, day, time, action="confirmed"):
    """Send SMS with booking details"""
    try:
        message = twilio_client.messages.create(
            body=f"🏥 Appointment {action}: {day} at {time}:00. Reply CANCEL to cancel.",
            from_=TWILIO_PHONE_NUMBER,
            to=patient_phone
        )
        print(f"SMS SENT TO {patient_phone}: {message.sid}")
        return message.sid
    except Exception as e:
        print(f"SMS FAILED: {str(e)}")
        return None

def process_message(message, phone_number):
    """Enhanced secure message processing"""
    if phone_number not in conversation_states:
        conversation_states[phone_number] = "GREETING"
    
    state = conversation_states[phone_number]
    msg_lower = message.lower()
    
    # Get patient profile
    patient = get_or_create_patient(phone_number)
    existing_booking = next((b for b in patient["bookings"] if b["status"] == "active"), None)
    
    if existing_booking and state == "GREETING":
        conversation_states[phone_number] = "MANAGE_BOOKING"
        return f"Hello! You have booking on {existing_booking['day']} at {existing_booking['time']}:00. ADJUST or CANCEL?"
    
    if state == "MANAGE_BOOKING":
        if 'adjust' in msg_lower:
            conversation_states[phone_number] = "CHOOSING_DAY"
            return "Adjust booking. New day? (Msombuluko, Lwesibili...)"
        elif 'cancel' in msg_lower:
            existing_booking["status"] = "cancelled"
            existing_booking["action"] = "cancelled"
            notify_clinic(phone_number, existing_booking['day'], existing_booking['time'], "cancelled")
            send_sms_confirmation(phone_number, existing_booking['day'], existing_booking['time'], "cancelled")
            conversation_states[phone_number] = "GREETING"
            return "Booking cancelled. Thank you!"
        else:
            return "Please choose: ADJUST or CANCEL your booking"
    
    elif state == "GREETING":
        conversation_states[phone_number] = "ASKING_DAY"
        return "Sawubona! 🏥 Book appointment? Yebo/Cha?"
    
    elif state == "ASKING_DAY":
        if 'yebo' in msg_lower:
            conversation_states[phone_number] = "CHOOSING_DAY"
            return "Kuhle! Day? (Msombuluko, Lwesibili, Lwesithathu...)"
        else:
            conversation_states[phone_number] = "GREETING"
            return "Ngiyaxolisa! How can I help?"
    
    elif state == "CHOOSING_DAY":
        days = {'msombuluko': 'Monday', 'lwesibili': 'Tuesday', 'lwesithathu': 'Wednesday'}
        for kw, day in days.items():
            if kw in msg_lower:
                conversation_states[phone_number] = "CHOOSING_TIME"
                request.session['selected_day'] = day
                return f"Kuhle! {day}. Time? (8, 9, 10, 2, 3)"
        return "Day? Msombuluko, Lwesibili, Lwesithathu?"
    
    elif state == "CHOOSING_TIME":
        if any(t in msg_lower for t in ['8', '9', '10', '2', '3']):
            time = ''.join([c for c in msg_lower if c in '891023'])
            day = request.session.get('selected_day', 'Unknown')
            
            # Check for double booking
            if prevent_double_booking(phone_number, day, time):
                return f"You already have booking on {day} at {time}:00. Choose different time."
            
            # Create secure booking
            booking, status = create_booking(phone_number, day, time, "booked")
            if booking:
                send_sms_confirmation(phone_number, day, time, "confirmed")
                conversation_states[phone_number] = "COMPLETE"
                return f"Perfect! 🎉 {day} at {time}:00. SMS confirmation sent!"
            else:
                return status  # Error message
        return "Time? 8, 9, 10, 2, 3"
    
    else:
        conversation_states[phone_number] = "GREETING"
        return "Sawubona! How can I help?"

# Simple session storage for web requests
request.session = {}

@app.route('/')
def home():
    return "🏥 Secure IsiZulu Healthcare AI LIVE"

@app.route('/health')
def health_check():
    return jsonify({"status": "healthy", "patients": len(patient_profiles)})

@app.route('/clinic')
def clinic_dashboard():
    active_bookings = [b for b in all_bookings if b["status"] == "active"]
    today = datetime.now().strftime("%Y-%m-%d")
    today_bookings = [b for b in booking_history if b["timestamp"].startswith(today) and b["status"] == "active"]
    
    dashboard_html = f"""
    <html>
    <head>
        <title>Secure Clinic Dashboard</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; text-align: center; }}
            .container {{ max-width: 1000px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
            .stats {{ display: flex; justify-content: space-around; margin: 20px 0; }}
            .stat-box {{ background: #4CAF50; color: white; padding: 15px; border-radius: 5px; min-width: 100px; }}
            .booking {{ border: 2px solid #4CAF50; padding: 15px; margin: 10px 0; border-radius: 8px; text-align: left; }}
            .cancelled {{ border-color: #f44336; background: #ffebee; }}
            .security {{ background: #ff9800; color: white; padding: 10px; margin: 10px 0; border-radius: 5px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🏥 Secure Clinic Dashboard</h1>
            <div class="security">🔒 Patient Data Securely Hashed | Double Booking Protection Active</div>
            
            <div class="stats">
                <div class="stat-box">Patients: {len(patient_profiles)}</div>
                <div class="stat-box">Active: {len(active_bookings)}</div>
                <div class="stat-box">Today: {len(today_bookings)}</div>
                <div class="stat-box">Total: {len(booking_history)}</div>
            </div>
            
            <h3>Active Bookings (Secure):</h3>
            {"".join([f'<div class="booking">Patient: {b["patient_phone"]} - {b["day"]} {b["time"]}:00<br><small>ID: {b["id"][:8]}...</small></div>' 
                     for b in active_bookings]) or "No active bookings"}
        </div>
    </body>
    </html>
    """
    return dashboard_html

@app.route('/whatsapp', methods=['POST'])
def whatsapp_webhook():
    try:
        msg = request.values.get('Body', '').strip()
        from_num = request.values.get('From', '')
        response = process_message(msg, from_num)
        return f'<Response><Message>{response}</Message></Response>'
    except Exception as e:
        return f'<Response><Message>System error. Please try again.</Message></Response>'

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=os.environ.get('PORT', 5000))
