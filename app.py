from flask import Flask, request, jsonify
import os
import hashlib
from datetime import datetime
from twilio.rest import Client

app = Flask(__name__)

# Twilio Configuration
TWILIO_ACCOUNT_SID = "AC055436adfbbdce3ea17cea0b3c1e6cc4"
TWILIO_AUTH_TOKEN = "172f1c5f53358211674cd9946baf3b0f" 
TWILIO_PHONE_NUMBER = "+12766242360"

# Initialize Twilio client
twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

# Secure Patient Database
patient_profiles = {}
conversation_states = {}
all_bookings = []
booking_history = []
selected_days = {}  # Simple day storage instead of session

def hash_phone(phone_number):
    return hashlib.sha256(phone_number.encode()).hexdigest()

def get_or_create_patient(phone_number):
    hashed_phone = hash_phone(phone_number)
    if hashed_phone not in patient_profiles:
        patient_profiles[hashed_phone] = {
            "phone": phone_number,
            "bookings": [],
            "created_date": datetime.now().isoformat()
        }
    return patient_profiles[hashed_phone]

def create_booking(patient_phone, day, time, action="booked"):
    patient = get_or_create_patient(patient_phone)
    
    booking_id = hashlib.md5(f"{patient_phone}{day}{time}{datetime.now()}".encode()).hexdigest()
    
    booking = {
        "id": booking_id,
        "patient_phone": patient_phone,
        "day": day,
        "time": time,
        "action": action,
        "status": "active" if action == "booked" else "cancelled",
        "timestamp": datetime.now().isoformat()
    }
    
    patient["bookings"].append(booking)
    all_bookings.append(booking)
    booking_history.append(booking)
    
    print(f"BOOKING: {action.upper()} - {patient_phone} on {day} at {time}:00")
    return booking

def send_sms_confirmation(patient_phone, day, time, action="confirmed"):
    try:
        message = twilio_client.messages.create(
            body=f"🏥 Appointment {action}: {day} at {time}:00",
            from_=TWILIO_PHONE_NUMBER,
            to=patient_phone
        )
        print(f"SMS SENT: {message.sid}")
        return message.sid
    except Exception as e:
        print(f"SMS FAILED: {e}")
        return None

def process_message(message, phone_number):
    if phone_number not in conversation_states:
        conversation_states[phone_number] = "GREETING"
    
    state = conversation_states[phone_number]
    msg_lower = message.lower()
    
    patient = get_or_create_patient(phone_number)
    existing_booking = next((b for b in patient["bookings"] if b["status"] == "active"), None)
    
    if existing_booking and state == "GREETING":
        conversation_states[phone_number] = "MANAGE_BOOKING"
        return f"You have booking on {existing_booking['day']} at {existing_booking['time']}:00. ADJUST or CANCEL?"
    
    if state == "MANAGE_BOOKING":
        if 'adjust' in msg_lower:
            conversation_states[phone_number] = "CHOOSING_DAY"
            return "New day? (Msombuluko, Lwesibili...)"
        elif 'cancel' in msg_lower:
            existing_booking["status"] = "cancelled"
            send_sms_confirmation(phone_number, existing_booking['day'], existing_booking['time'], "cancelled")
            conversation_states[phone_number] = "GREETING"
            return "Booking cancelled. Thank you!"
        else:
            return "ADJUST or CANCEL?"
    
    elif state == "GREETING":
        conversation_states[phone_number] = "ASKING_DAY"
        return "Sawubona! Book appointment? Yebo/Cha?"
    
    elif state == "ASKING_DAY":
        if 'yebo' in msg_lower:
            conversation_states[phone_number] = "CHOOSING_DAY"
            return "Day? (Msombuluko, Lwesibili, Lwesithathu...)"
        else:
            conversation_states[phone_number] = "GREETING"
            return "How can I help?"
    
    elif state == "CHOOSING_DAY":
        days = {'msombuluko': 'Monday', 'lwesibili': 'Tuesday', 'lwesithathu': 'Wednesday'}
        for kw, day in days.items():
            if kw in msg_lower:
                conversation_states[phone_number] = "CHOOSING_TIME"
                selected_days[phone_number] = day  # Store day
                return f"Kuhle! {day}. Time? (8, 9, 10, 2, 3)"
        return "Day? Msombuluko, Lwesibili, Lwesithathu?"
    
    elif state == "CHOOSING_TIME":
        if any(t in msg_lower for t in ['8', '9', '10', '2', '3']):
            time = ''.join([c for c in msg_lower if c in '891023'])
            day = selected_days.get(phone_number, "Unknown")
            
            booking = create_booking(phone_number, day, time, "booked")
            send_sms_confirmation(phone_number, day, time, "confirmed")
            conversation_states[phone_number] = "COMPLETE"
            return f"Perfect! 🎉 {day} at {time}:00. SMS sent!"
        return "Time? 8, 9, 10, 2, 3"
    
    else:
        conversation_states[phone_number] = "GREETING"
        return "Sawubona! How can I help?"

@app.route('/')
def home():
    return "🏥 IsiZulu Healthcare AI LIVE"

@app.route('/health')
def health_check():
    return jsonify({"status": "healthy", "patients": len(patient_profiles)})

@app.route('/clinic')
def clinic_dashboard():
    active_bookings = [b for b in all_bookings if b["status"] == "active"]
    
    dashboard_html = f"""
    <html>
    <head><title>Clinic Dashboard</title>
    <style>
        body {{ font-family: Arial; margin: 20px; background: #f5f5f5; text-align: center; }}
        .container {{ max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; }}
        .stats {{ display: flex; justify-content: space-around; margin: 20px 0; }}
        .stat-box {{ background: #4CAF50; color: white; padding: 15px; border-radius: 5px; }}
        .booking {{ border: 2px solid #4CAF50; padding: 15px; margin: 10px 0; border-radius: 8px; text-align: left; }}
    </style>
    </head>
    <body>
        <div class="container">
            <h1>🏥 Clinic Dashboard</h1>
            <div class="stats">
                <div class="stat-box">Patients: {len(patient_profiles)}</div>
                <div class="stat-box">Active: {len(active_bookings)}</div>
            </div>
            <h3>Active Bookings:</h3>
            {"".join([f'<div class="booking">{b["patient_phone"]} - {b["day"]} {b["time"]}:00</div>' 
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
        return f'<Response><Message>System error. Try again.</Message></Response>'

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=os.environ.get('PORT', 5000))
