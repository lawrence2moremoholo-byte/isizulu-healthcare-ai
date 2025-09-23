from flask import Flask, request, jsonify
import os
from datetime import datetime

app = Flask(__name__)

# Storage
conversation_states = {}
current_days = {}
all_bookings = []
booking_history = []

def notify_clinic(patient_phone, day, time, action="booked"):
    booking = {"patient": patient_phone, "day": day, "time": time, "action": action, "timestamp": datetime.now().isoformat()}
    all_bookings.append(booking)
    booking_history.append(booking)
    print(f"CLINIC: {action.upper()} - {patient_phone} on {day} at {time}:00")

def send_sms_confirmation(patient_phone, day, time, action="confirmed"):
    # TODO: Integrate SMS API
    sms_msg = f"Appointment {action}: {day} at {time}:00. Reply CANCEL to cancel."
    print(f"SMS to {patient_phone}: {sms_msg}")

def process_message(message, phone_number):
    if phone_number not in conversation_states:
        conversation_states[phone_number] = "GREETING"
    
    state = conversation_states[phone_number]
    msg_lower = message.lower()
    
    # Check if user has existing booking
    existing_booking = next((b for b in all_bookings if b['patient'] == phone_number and b['action'] == 'booked'), None)
    
    if existing_booking and state == "GREETING":
        conversation_states[phone_number] = "MANAGE_BOOKING"
        return "You have an existing booking. ADJUST or CANCEL?"
    
    if state == "MANAGE_BOOKING":
        if 'adjust' in msg_lower or 'change' in msg_lower:
            conversation_states[phone_number] = "CHOOSING_DAY"
            return "Adjust booking. New day? (Msombuluko, Lwesibili...)"
        elif 'cancel' in msg_lower:
            # Cancel existing booking
            existing_booking['action'] = 'cancelled'
            notify_clinic(phone_number, existing_booking['day'], existing_booking['time'], "cancelled")
            send_sms_confirmation(phone_number, existing_booking['day'], existing_booking['time'], "cancelled")
            conversation_states[phone_number] = "GREETING"
            return "Booking cancelled. Sawubona!"
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
                current_days[phone_number] = day
                return f"Kuhle! {day}. Time? (8, 9, 10, 2, 3)"
        return "Day? Msombuluko, Lwesibili, Lwesithathu?"
    
    elif state == "CHOOSING_TIME":
        if any(t in msg_lower for t in ['8', '9', '10', '2', '3']):
            time = ''.join([c for c in msg_lower if c in '891023'])
            day = current_days.get(phone_number, "Unknown")
            
            # Cancel old booking if adjusting
            old_booking = next((b for b in all_bookings if b['patient'] == phone_number and b['action'] == 'booked'), None)
            if old_booking:
                old_booking['action'] = 'cancelled'
                notify_clinic(phone_number, old_booking['day'], old_booking['time'], "cancelled")
            
            notify_clinic(phone_number, day, time, "booked")
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
    return jsonify({"status": "healthy"})

@app.route('/clinic')
def clinic_dashboard():
    # Statistics
    today = datetime.now().strftime("%Y-%m-%d")
    today_bookings = [b for b in booking_history if b['timestamp'].startswith(today) and b['action'] == 'booked']
    weekly_bookings = len([b for b in booking_history if b['action'] == 'booked'])  # Simplified
    
    dashboard_html = f"""
    <html>
    <head>
        <title>Clinic Dashboard</title>
        <style>
            body {{ 
                font-family: Arial, sans-serif; 
                margin: 0; 
                padding: 20px; 
                background: #f5f5f5;
                text-align: center;
            }}
            .container {{ 
                max-width: 800px; 
                margin: 0 auto; 
                background: white; 
                padding: 30px; 
                border-radius: 10px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }}
            .stats {{ 
                display: flex; 
                justify-content: space-around; 
                margin: 20px 0; 
            }}
            .stat-box {{ 
                background: #4CAF50; 
                color: white; 
                padding: 15px; 
                border-radius: 5px; 
                min-width: 100px;
            }}
            .booking {{ 
                border: 2px solid #4CAF50; 
                padding: 15px; 
                margin: 10px 0; 
                border-radius: 8px;
                text-align: left;
            }}
            .cancelled {{ 
                border-color: #f44336; 
                background: #ffebee;
            }}
            h1 {{ color: #2E7D32; }}
            button {{ 
                background: #2196F3; 
                color: white; 
                padding: 10px 15px; 
                border: none; 
                border-radius: 5px; 
                margin: 5px;
                cursor: pointer;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🏥 Clinic Dashboard</h1>
            
            <div class="stats">
                <div class="stat-box">Today: {len(today_bookings)}</div>
                <div class="stat-box">Weekly: {weekly_bookings}</div>
                <div class="stat-box">Monthly: {weekly_bookings * 4}</div>
                <div class="stat-box">Yearly: {weekly_bookings * 52}</div>
            </div>
            
            <h3>Active Bookings:</h3>
            {"".join([f'<div class="booking">{b["patient"]} - {b["day"]} {b["time"]}:00</div>' 
                     for b in all_bookings if b['action'] == 'booked']) or "No active bookings"}
            
            <h3>Recent Activity:</h3>
            {"".join([f'<div class="booking {b["action"]}">{b["action"].upper()}: {b["patient"]} - {b["day"]} {b["time"]}:00</div>' 
                     for b in booking_history[-10:]]) or "No activity"}
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
        return f'<Response><Message>Error: {str(e)}</Message></Response>'

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=os.environ.get('PORT', 5000))
