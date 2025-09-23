from flask import Flask, request, jsonify
import os

app = Flask(__name__)

# Store conversations and bookings
conversation_states = {}
current_days = {}
all_bookings = []

def notify_clinic(patient_phone, day, time):
    """TODO: Actually send WhatsApp/email to clinic"""
    booking_msg = f"NEW BOOKING: {patient_phone} on {day} at {time}:00"
    print(f"CLINIC SHOULD GET: {booking_msg}")
    all_bookings.append({"patient": patient_phone, "day": day, "time": time})
    return booking_msg

def process_message(message, phone_number):
    if phone_number not in conversation_states:
        conversation_states[phone_number] = "GREETING"
    
    state = conversation_states[phone_number]
    msg_lower = message.lower()
    
    if state == "GREETING":
        conversation_states[phone_number] = "ASKING_DAY"
        return "Sawubona! 🏥 Ufuna ukubona udokotela? Yebo noma Cha?"
    
    elif state == "ASKING_DAY":
        if 'yebo' in msg_lower:
            conversation_states[phone_number] = "CHOOSING_DAY"
            return "Kuhle! Ufuna usuku luni? (Msombuluko, Lwesibili, Lwesithathu...)"
        else:
            conversation_states[phone_number] = "GREETING"
            return "Ngiyaxolisa! Ngingakusiza ngani?"
    
    elif state == "CHOOSING_DAY":
        days = {'msombuluko': 'Msombuluko', 'lwesibili': 'Lwesibili', 'lwesithathu': 'Lwesithathu'}
        for kw, day in days.items():
            if kw in msg_lower:
                conversation_states[phone_number] = "CHOOSING_TIME"
                current_days[phone_number] = day
                return f"Kuhle! Ukhethe u-{day}. Ukhetha isikhathi sini? (8am, 9am, 10am, 2pm, 3pm)"
        return "Angikwazi usuku. Msombuluko, Lwesibili, Lwesithathu?"
    
    elif state == "CHOOSING_TIME":
        if any(t in msg_lower for t in ['8am', '9am', '10am', '2pm', '3pm']):
            time = ''.join([c for c in msg_lower if c in '891023'])
            day = current_days.get(phone_number, "Unknown")
            notify_clinic(phone_number, day, time)  # Store booking
            conversation_states[phone_number] = "COMPLETE"
            return f"Perfect! 🎉 Isikhathi sakho {time}:00 sihleliwe. Suzohamba kahle!"
        return "Sicela isikhathi: 8am, 9am, 10am, 2pm, noma 3pm"
    
    else:
        conversation_states[phone_number] = "GREETING"
        return "Sawubona! Ngingakusiza kanjani?"

@app.route('/')
def home():
    return "🏥 IsiZulu Healthcare AI LIVE"

@app.route('/health')
def health_check():
    return jsonify({"status": "healthy"})

@app.route('/clinic')
def clinic_dashboard():
    bookings_html = "".join([f"<div>{b['patient']} - {b['day']} {b['time']}:00</div>" for b in all_bookings])
    return f"""
    <html><body>
        <h1>🏥 Clinic Dashboard</h1>
        <h3>All Bookings:</h3>
        {bookings_html if bookings_html else "No bookings yet"}
    </body></html>
    """

@app.route('/whatsapp', methods=['POST'])
def whatsapp_webhook():
    try:
        msg = request.values.get('Body', '').strip()
        from_num = request.values.get('From', '')
        response = process_message(msg, from_num)
        return f'<Response><Message>{response}</Message></Response>'
    except:
        return '<Response><Message>Error. Try again.</Message></Response>'

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=os.environ.get('PORT', 5000))
