from flask import Flask, request, jsonify, Response
import os
import hashlib
from datetime import datetime, timedelta
from twilio.rest import Client

app = Flask(__name__)

# Twilio Configuration
TWILIO_ACCOUNT_SID = "AC055436adfbbdce3ea17cea0b3c1e6cc4"
TWILIO_AUTH_TOKEN = "172f1c5f53358211674cd9946baf3b0f" 
TWILIO_PHONE_NUMBER = "+12766242360"

twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

# Clinic Business Rules
CLINIC_HOURS = {
    "Monday": ["08:00", "09:00", "10:00", "14:00", "15:00"],
    "Tuesday": ["08:00", "09:00", "10:00", "14:00", "15:00"],
    "Wednesday": ["08:00", "09:00", "10:00", "14:00", "15:00"],
    "Thursday": ["08:00", "09:00", "10:00", "14:00", "15:00"],
    "Friday": ["08:00", "09:00", "10:00", "14:00", "15:00"],
    "Saturday": ["09:00", "10:00"],
    "Sunday": []  # Closed
}

MAX_ADVANCE_DAYS = 3  # Patients can only book 3 days in advance
MAX_DAILY_SLOTS = 5   # Max appointments per day

# Data Storage
patient_profiles = {}
conversation_states = {}
all_bookings = []
booking_history = {}
selected_days = {}

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

def get_available_days():
    """Get days available for booking (next 3 days)"""
    today = datetime.now()
    available_days = []
    
    for i in range(1, MAX_ADVANCE_DAYS + 1):  # Start from tomorrow
        future_date = today + timedelta(days=i)
        day_name = future_date.strftime("%A")  # Monday, Tuesday, etc.
        
        # Check if clinic is open and has available slots
        if day_name in CLINIC_HOURS and CLINIC_HOURS[day_name]:
            # Count booked slots for this day
            booked_count = len([b for b in all_bookings 
                              if b["day"] == day_name and b["status"] == "active"])
            
            if booked_count < MAX_DAILY_SLOTS:
                available_days.append(day_name)
    
    return available_days

def get_available_slots(day_name):
    """Get available time slots for a specific day"""
    if day_name not in CLINIC_HOURS:
        return []
    
    all_slots = CLINIC_HOURS[day_name]
    
    # Get booked slots for this day
    booked_slots = [b["time"] for b in all_bookings 
                   if b["day"] == day_name and b["status"] == "active"]
    
    # Return available slots (not booked yet)
    available_slots = [slot for slot in all_slots if slot not in booked_slots]
    
    return available_slots

def is_day_available(day_name):
    """Check if a day has any available slots"""
    return len(get_available_slots(day_name)) > 0

def create_booking(patient_phone, day, time, action="booked"):
    patient = get_or_create_patient(patient_phone)
    
    # Verify slot is still available
    if time not in get_available_slots(day):
        return None, "Sorry, that time slot was just taken. Please choose another time."
    
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
    
    print(f"BOOKING: {action.upper()} - {patient_phone} on {day} at {time}")
    return booking, "success"

def send_sms_confirmation(patient_phone, day, time, action="confirmed"):
    try:
        message = twilio_client.messages.create(
            body=f"🏥 Appointment {action}: {day} at {time}. Reply CANCEL to cancel.",
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
        return f"You have booking on {existing_booking['day']} at {existing_booking['time']}. ADJUST or CANCEL?"
    
    if state == "MANAGE_BOOKING":
        if 'adjust' in msg_lower:
            conversation_states[phone_number] = "SHOW_AVAILABLE_DAYS"
            return "Let me check available days..."
        elif 'cancel' in msg_lower:
            existing_booking["status"] = "cancelled"
            send_sms_confirmation(phone_number, existing_booking['day'], existing_booking['time'], "cancelled")
            conversation_states[phone_number] = "GREETING"
            return "Booking cancelled. Thank you!"
        else:
            return "ADJUST or CANCEL?"
    
    elif state == "GREETING":
        conversation_states[phone_number] = "SHOW_AVAILABLE_DAYS"
        return "Sawubona! Checking available appointment days..."
    
    elif state == "SHOW_AVAILABLE_DAYS":
        available_days = get_available_days()
        
        if not available_days:
            conversation_states[phone_number] = "GREETING"
            return "Sorry, no appointments available in the next 3 days. Try again tomorrow."
        
        days_list = ", ".join(available_days)
        conversation_states[phone_number] = "CHOOSING_DAY"
        return f"Available days: {days_list}. Which day works for you?"
    
    elif state == "CHOOSING_DAY":
        available_days = get_available_days()
        selected_day = None
        
        # Map isiZulu days to English
        day_map = {
            'msombuluko': 'Monday', 'lwesibili': 'Tuesday', 'lwesithathu': 'Wednesday',
            'lwesine': 'Thursday', 'lwesihlanu': 'Friday', 'mgqibelo': 'Saturday'
        }
        
        for kw, day in day_map.items():
            if kw in msg_lower and day in available_days:
                selected_day = day
                break
        
        if selected_day:
            selected_days[phone_number] = selected_day
            conversation_states[phone_number] = "SHOW_AVAILABLE_SLOTS"
            return f"Checking available times for {selected_day}..."
        else:
            return f"Please choose from available days: {', '.join(available_days)}"
    
    elif state == "SHOW_AVAILABLE_SLOTS":
        day = selected_days.get(phone_number)
        if not day:
            conversation_states[phone_number] = "SHOW_AVAILABLE_DAYS"
            return "Let me show available days again..."
        
        available_slots = get_available_slots(day)
        
        if not available_slots:
            conversation_states[phone_number] = "SHOW_AVAILABLE_DAYS"
            return f"No slots available on {day}. Choose another day: {', '.join(get_available_days())}"
        
        slots_list = ", ".join(available_slots)
        conversation_states[phone_number] = "CHOOSING_TIME"
        return f"Available times on {day}: {slots_list}. Which time?"
    
    elif state == "CHOOSING_TIME":
        day = selected_days.get(phone_number)
        available_slots = get_available_slots(day) if day else []
        
        selected_time = None
        for slot in available_slots:
            if slot.replace(":00", "") in msg_lower:  # Match "8" with "08:00"
                selected_time = slot
                break
        
        if selected_time:
            booking, status = create_booking(phone_number, day, selected_time, "booked")
            if booking:
                send_sms_confirmation(phone_number, day, selected_time, "confirmed")
                conversation_states[phone_number] = "COMPLETE"
                return f"Perfect! 🎉 Booking confirmed for {day} at {selected_time}. SMS sent!"
            else:
                return status
        else:
            return f"Please choose from available times: {', '.join(available_slots)}"
    
    else:
        conversation_states[phone_number] = "GREETING"
        return "Sawubona! How can I help?"

@app.route('/')
def home():
    return "🏥 Professional Booking System LIVE"

@app.route('/health')
def health_check():
    return jsonify({
        "status": "healthy", 
        "patients": len(patient_profiles),
        "available_days": get_available_days()
    })

@app.route('/clinic')
def clinic_dashboard():
    active_bookings = [b for b in all_bookings if b["status"] == "active"]
    available_days = get_available_days()
    
    # Show availability for next 3 days
    availability_html = ""
    for day in available_days:
        slots = get_available_slots(day)
        availability_html += f"<div>{day}: {len(slots)} slots available</div>"
    
    dashboard_html = f"""
    <html>
    <head><title>Clinic Dashboard</title>
    <style>
        body {{ font-family: Arial; margin: 20px; background: #f5f5f5; text-align: center; }}
        .container {{ max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; }}
        .stats {{ display: flex; justify-content: space-around; margin: 20px 0; }}
        .stat-box {{ background: #4CAF50; color: white; padding: 15px; border-radius: 5px; }}
        .booking {{ border: 2px solid #4CAF50; padding: 15px; margin: 10px 0; border-radius: 8px; text-align: left; }}
        .availability {{ background: #2196F3; color: white; padding: 15px; margin: 10px 0; border-radius: 8px; }}
    </style>
    </head>
    <body>
        <div class="container">
            <h1>🏥 Professional Clinic Dashboard</h1>
            
            <div class="availability">
                <h3>Next 3 Days Availability:</h3>
                {availability_html if availability_html else "No availability in next 3 days"}
            </div>
            
            <div class="stats">
                <div class="stat-box">Patients: {len(patient_profiles)}</div>
                <div class="stat-box">Active: {len(active_bookings)}</div>
                <div class="stat-box">Max/Day: {MAX_DAILY_SLOTS}</div>
            </div>
            
            <h3>Active Bookings:</h3>
            {"".join([f'<div class="booking">{b["patient_phone"]} - {b["day"]} {b["time"]}</div>' 
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
        
        xml_response = f'<?xml version="1.0" encoding="UTF-8"?><Response><Message>{response}</Message></Response>'
        return Response(xml_response, mimetype='text/xml')
        
    except Exception as e:
        error_xml = '<?xml version="1.0" encoding="UTF-8"?><Response><Message>System error. Try again.</Message></Response>'
        return Response(error_xml, mimetype='text/xml')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=os.environ.get('PORT', 5000))
