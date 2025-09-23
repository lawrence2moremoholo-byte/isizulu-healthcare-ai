from flask import Flask, request, jsonify, Response
import os
import hashlib
import json
from datetime import datetime, timedelta
from twilio.rest import Client

app = Flask(__name__)

# Twilio Configuration
TWILIO_ACCOUNT_SID = "AC055436adfbbdce3ea17cea0b3c1e6cc4"
TWILIO_AUTH_TOKEN = "172f1c5f53358211674cd9946baf3b0f" 
TWILIO_PHONE_NUMBER = "+12766242360"
twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

# Clinic Configuration IN ISIZULU
CLINIC_HOURS = {
    "Msombuluko": ["08:00", "09:00", "10:00", "14:00", "15:00"],
    "Lwesibili": ["08:00", "09:00", "10:00", "14:00", "15:00"],
    "Lwesithathu": ["08:00", "09:00", "10:00", "14:00", "15:00"],
    "Lwesine": ["08:00", "09:00", "10:00", "14:00", "15:00"],
    "Lwesihlanu": ["08:00", "09:00", "10:00", "14:00", "15:00"],
    "Mgqibelo": ["09:00", "10:00"],
    "Sonto": []
}

MAX_ADVANCE_DAYS = 3
MAX_DAILY_SLOTS = 5

# Data Storage with Persistence
def load_data():
    try:
        with open('data.json', 'r') as f:
            data = json.load(f)
            return data.get("patients", {}), data.get("conversations", {}), data.get("bookings", [])
    except:
        return {}, {}, []

def save_data():
    with open('data.json', 'w') as f:
        json.dump({
            "patients": patient_profiles,
            "conversations": conversation_states, 
            "bookings": all_bookings
        }, f)

# Load existing data
patient_profiles, conversation_states, all_bookings = load_data()
selected_days = {}

# isiZulu Day Mapping
EN_TO_ZULU = {
    "Monday": "Msombuluko", "Tuesday": "Lwesibili", "Wednesday": "Lwesithathu",
    "Thursday": "Lwesine", "Friday": "Lwesihlanu", "Saturday": "Mgqibelo", "Sunday": "Sonto"
}

ZULU_TO_EN = {v: k for k, v in EN_TO_ZULU.items()}

def get_available_days():
    """Get next 3 days in ISIZULU"""
    today = datetime.now()
    available_days = []
    
    for i in range(1, MAX_ADVANCE_DAYS + 1):
        future_date = today + timedelta(days=i)
        day_name_en = future_date.strftime("%A")
        day_name_zulu = EN_TO_ZULU.get(day_name_en)
        
        if day_name_zulu and day_name_zulu in CLINIC_HOURS and CLINIC_HOURS[day_name_zulu]:
            booked_count = len([b for b in all_bookings 
                              if b["day"] == day_name_zulu and b["status"] == "active"])
            
            if booked_count < MAX_DAILY_SLOTS:
                available_days.append(day_name_zulu)
    
    return available_days

def get_available_slots(day_zulu):
    """Get available slots for ISIZULU day"""
    if day_zulu not in CLINIC_HOURS:
        return []
    
    booked_slots = [b["time"] for b in all_bookings 
                   if b["day"] == day_zulu and b["status"] == "active"]
    
    return [slot for slot in CLINIC_HOURS[day_zulu] if slot not in booked_slots]

def create_booking(patient_phone, day_zulu, time, action="booked"):
    if time not in get_available_slots(day_zulu):
        return None, "Izikhathi zivaliwe. Sicela ukhethe esinye isikhathi."
    
    booking_id = hashlib.md5(f"{patient_phone}{day_zulu}{time}{datetime.now()}".encode()).hexdigest()
    
    booking = {
        "id": booking_id,
        "patient_phone": patient_phone,
        "day": day_zulu,  # Store in isiZulu
        "time": time,
        "action": action,
        "status": "active",
        "timestamp": datetime.now().isoformat(),
        "language": "isiZulu"
    }
    
    all_bookings.append(booking)
    save_data()  # Persist to file
    
    return booking, "success"

def send_sms_confirmation(patient_phone, day_zulu, time, action="confirmed"):
    action_text = "siqinisekisiwe" if action == "confirmed" else "ikhanseliwe"
    try:
        message = twilio_client.messages.create(
            body=f"🏥 Isikhathi sakho {action_text}: {day_zulu} ngo {time}.",
            from_=TWILIO_PHONE_NUMBER,
            to=patient_phone
        )
        return message.sid
    except:
        return None

def process_message(message, phone_number):
    msg_lower = message.lower()
    
    if phone_number not in conversation_states:
        conversation_states[phone_number] = "GREETING"
    
    state = conversation_states[phone_number]
    
    # Complete isiZulu conversation flow
    if state == "GREETING":
        conversation_states[phone_number] = "SHOW_DAYS"
        save_data()
        return "Sawubona! 🏥 Ngabe ufuna isikhathi sokubona udokotela? Yebo/Cha"
    
    elif state == "SHOW_DAYS":
        if 'yebo' in msg_lower:
            available_days = get_available_days()
            if not available_days:
                return "Izinsuku zivaliwe. Zama futhi kusasa."
            days_str = ", ".join(available_days)
            conversation_states[phone_number] = "CHOOSE_DAY"
            save_data()
            return f"Izinsuku ezitholakalayo: {days_str}. Ufuna usuku luni?"
        else:
            return "Ngiyaxolisa! Ngingakusiza ngani?"
    
    elif state == "CHOOSE_DAY":
        available_days = get_available_days()
        chosen_day = None
        
        for day_zulu in available_days:
            if day_zulu.lower() in msg_lower:
                chosen_day = day_zulu
                break
        
        if chosen_day:
            selected_days[phone_number] = chosen_day
            conversation_states[phone_number] = "SHOW_SLOTS"
            save_data()
            return f"Kuhle! Ukhethe u-{chosen_day}. Ngizobheka izikhathi..."
        else:
            return f"Sicela ukhethe usuku: {', '.join(available_days)}"
    
    elif state == "SHOW_SLOTS":
        day_zulu = selected_days.get(phone_number)
        slots = get_available_slots(day_zulu) if day_zulu else []
        
        if not slots:
            conversation_states[phone_number] = "SHOW_DAYS"
            save_data()
            return f"Azikho izikhathi ku-{day_zulu}. Khetha olunye usuku."
        
        slots_str = ", ".join(slots)
        conversation_states[phone_number] = "CHOOSE_TIME"
        save_data()
        return f"Izikhathi ku-{day_zulu}: {slots_str}. Ufuna isikhathi sini?"
    
    elif state == "CHOOSE_TIME":
        day_zulu = selected_days.get(phone_number)
        slots = get_available_slots(day_zulu) if day_zulu else []
        
        chosen_time = None
        for slot in slots:
            if slot.replace(":00", "") in msg_lower:
                chosen_time = slot
                break
        
        if chosen_time:
            booking, status = create_booking(phone_number, day_zulu, chosen_time)
            if booking:
                send_sms_confirmation(phone_number, day_zulu, chosen_time)
                conversation_states[phone_number] = "COMPLETE"
                save_data()
                return f"Kuhle! 🎉 Isikhathi sakho sihleliwe ku-{day_zulu} ngo-{chosen_time}. Izilongozi zithunyelwe!"
            else:
                return status
        else:
            return f"Sicela ukhethe isikhathi: {', '.join(slots)}"
    
    else:
        conversation_states[phone_number] = "GREETING"
        save_data()
        return "Sawubona! Ngingakusiza kanjani?"

# Routes remain the same as before...
@app.route('/')
def home():
    return "🏥 IsiZulu Healthcare System LIVE"

@app.route('/clinic')
def clinic_dashboard():
    active_bookings = [b for b in all_bookings if b["status"] == "active"]
    
    stats_html = f"""
    <div class="stats">
        <div class="stat-box">Abaguli: {len(patient_profiles)}</div>
        <div class="stat-box">Izikhathi: {len(active_bookings)}</div>
        <div class="stat-box">Ulimi: isiZulu 100%</div>
    </div>
    """
    
    # Full HTML as before...
    return f"<html>...{stats_html}...</html>"

@app.route('/whatsapp', methods=['POST'])
def whatsapp_webhook():
    try:
        msg = request.values.get('Body', '').strip()
        from_num = request.values.get('From', '')
        response = process_message(msg, from_num)
        
        xml_response = f'<?xml version="1.0" encoding="UTF-8"?><Response><Message>{response}</Message></Response>'
        return Response(xml_response, mimetype='text/xml')
    except Exception as e:
        error_xml = '<?xml version="1.0" encoding="UTF-8"?><Response><Message>Iputha elicindezelayo. Zama futhi.</Message></Response>'
        return Response(error_xml, mimetype='text/xml')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=os.environ.get('PORT', 5000))
