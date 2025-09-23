from flask import Flask, request, jsonify
import os

app = Flask(__name__)

# Conversation state tracking
conversation_states = {}
current_days = {}

def notify_clinic(patient_phone, day, time):
    """Send WhatsApp notification to clinic staff"""
    clinic_number = "+2767..."  # You'll set this per client
    
    notification_msg = f"📋 NEW APPOINTMENT:\nPatient: {patient_phone}\nDay: {day}\nTime: {time}:00\n\nView all: https://isizulu-healthcare-ai.onrender.com/clinic"
    
    # In production, you'd send via Twilio API
    # For now, we'll print it (you'll see in Render logs)
    print(f"CLINIC NOTIFICATION: {notification_msg}")
    return notification_msg

def process_message(message, phone_number):
    # Get or create conversation state for this user
    if phone_number not in conversation_states:
        conversation_states[phone_number] = "GREETING"
    
    current_state = conversation_states[phone_number]
    message_lower = message.lower()
    
    # State machine
    if current_state == "GREETING":
        conversation_states[phone_number] = "ASKING_DAY"
        return "Sawubona! 🏥 Ufuna ukubona udokotela? Yebo cha?"
    
    elif current_state == "ASKING_DAY":
        if 'yebo' in message_lower or 'yes' in message_lower:
            conversation_states[phone_number] = "CHOOSING_DAY"
            return "Kuhle! Ufuna usuku luni? (Msombuluko, Lwesibili, Lwesithathu, Lwesine, Lwesihlanu, Mgqibelo)"
        else:
            conversation_states[phone_number] = "GREETING"
            return "Ngiyaxolisa! Ngingakusiza ngani?"
    
    elif current_state == "CHOOSING_DAY":
        day_keywords = {
            'msombuluko': 'Msombuluko', 'lwesibili': 'Lwesibili', 
            'lwesithathu': 'Lwesithathu', 'lwesine': 'Lwesine',
            'lwesihlanu': 'Lwesihlanu', 'mgqibelo': 'Mgqibelo'
        }
        
        for keyword, day in day_keywords.items():
            if keyword in message_lower:
                conversation_states[phone_number] = "CHOOSING_TIME"
                current_days[phone_number] = day  # Store selected day
                return f"Kuhle! Ukhethe u-{day}. Ufuna isikhathi sini? (8, 9, 10, 2, 3)"
        
        return "Angikwazi usuku. Sicela uthi: Msombuluko, Lwesibili, Lwesithathu, njll."
    
    elif current_state == "CHOOSING_TIME":
        if any(word in message_lower for word in ['8', '9', '10', '2', '3']):
            selected_time = ''.join([char for char in message_lower if char in '891023'])
            current_day = current_days.get(phone_number, "Unknown")
            
            # NOTIFY CLINIC
            clinic_msg = notify_clinic(phone_number, current_day, selected_time)
            
            conversation_states[phone_number] = "COMPLETE"
            return f"Perfect! 🎉 Isikhathi sakho sihleliwe ngo {selected_time}:00. Sizohamba kahle!"
        else:
            return "Sicela unikeze isikhathi: 8, 9, 10, 2, noma 3"
    
    else:
        conversation_states[phone_number] = "GREETING"
        return "Sawubona! Ngingakusiza kanjani ngokubuka udokotela?"

@app.route('/')
def home():
    return "🏥 IsiZulu Healthcare AI is LIVE!"

@app.route('/health')
def health_check():
    return jsonify({"status": "healthy", "service": "isizulu_healthcare"})

# Clinic Dashboard
@app.route('/clinic')
def clinic_dashboard():
    dashboard_html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Clinic Appointments</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; }
            .appointment { border: 1px solid #ccc; padding: 15px; margin: 10px 0; border-radius: 5px; }
            .today { background-color: #f0fff0; }
        </style>
    </head>
    <body>
        <h1>🏥 Clinic Appointments Dashboard</h1>
        <h3>Today's Bookings</h3>
        <div id="bookings">
            <div class="appointment today">
                <strong>Patient:</strong> +27XXX XXX XXX<br>
                <strong>Day:</strong> Monday<br>
                <strong>Time:</strong> 9:00
            </div>
        </div>
        <p><em>Live booking updates will appear here automatically.</em></p>
        <p>Share this link with clinic staff: https://isizulu-healthcare-ai.onrender.com/clinic</p>
    </body>
    </html>
    """
    return dashboard_html

@app.route('/whatsapp', methods=['POST'])
def whatsapp_webhook():
    try:
        incoming_msg = request.values.get('Body', '').strip()
        from_number = request.values.get('From', '')
        
        response_text = process_message(incoming_msg, from_number)
        
        return f'<Response><Message>{response_text}</Message></Response>'
        
    except Exception as e:
        return f'<Response><Message>Ngiyaxolisa, iphutha lifikile.</Message></Response>'

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=os.environ.get('PORT', 5000))
