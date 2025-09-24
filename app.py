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

# Clinic Configuration
CLINIC_HOURS = {
    "Monday": ["08:00", "09:00", "10:00", "14:00", "15:00"],
    "Tuesday": ["08:00", "09:00", "10:00", "14:00", "15:00"],
    "Wednesday": ["08:00", "09:00", "10:00", "14:00", "15:00"],
    "Thursday": ["08:00", "09:00", "10:00", "14:00", "15:00"],
    "Friday": ["08:00", "09:00", "10:00", "14:00", "15:00"],
    "Saturday": ["09:00", "10:00"],
    "Sunday": []
}

MAX_ADVANCE_DAYS = 3
MAX_DAILY_SLOTS = 5

# COMPLETE 11 South African Languages - NO EXTERNAL DEPENDENCIES
LANGUAGE_CONFIG = {
    'english': {
        'code': 'en',
        'name': 'English',
        'days': {
            'Monday': 'Monday', 'Tuesday': 'Tuesday', 'Wednesday': 'Wednesday',
            'Thursday': 'Thursday', 'Friday': 'Friday', 'Saturday': 'Saturday', 'Sunday': 'Sunday'
        },
        'responses': {
            'welcome': "Welcome to MetaWell AI Clinic! Choose language: 1.English 2.isZulu 3.isXhosa 4.Afrikaans 5.Sesotho 6.Setswana 7.Sepedi 8.Xitsonga 9.Tshivenda 10.isNdebele 11.siSwati",
            'greeting': "Hello! Book medical appointment? (Yes/No)",
            'show_days': "Available days: {days}. Which day?",
            'choose_day': "Great! You chose {day}. Checking times...",
            'show_slots': "Times on {day}: {slots}. Which time?",
            'booking_success': "✅ Confirmed! {day} at {time}. SMS sent!",
            'goodbye': "Thank you! Goodbye!",
            'yes': ['yes', 'y'], 'no': ['no', 'n']
        }
    },
    'isizulu': {
        'code': 'zu',
        'name': 'isiZulu',
        'days': {
            'Monday': 'Msombuluko', 'Tuesday': 'Lwesibili', 'Wednesday': 'Lwesithathu',
            'Thursday': 'Lwesine', 'Friday': 'Lwesihlanu', 'Saturday': 'Mgqibelo', 'Sunday': 'Sonto'
        },
        'responses': {
            'welcome': "Uyemukelwa ku-MetaWell AI! Khetha ulimi: 1.isZulu 2.English 3.isXhosa 4.Afrikaans 5.Sesotho 6.Setswana 7.Sepedi 8.Xitsonga 9.Tshivenda 10.isNdebele 11.siSwati",
            'greeting': "Sawubona! Bhuka isikhathi? (Yebo/Cha)",
            'show_days': "Izinsuku: {days}. Usuku luni?",
            'choose_day': "Kuhle! U-{day}. Ngibheka izikhathi...",
            'show_slots': "Izikhathi ku-{day}: {slots}. Isikhathi sini?",
            'booking_success': "✅ Siqinisekisiwe! {day} nge-{time}. SMS ithunyelwe!",
            'goodbye': "Ngiyabonga! Sala kahle!",
            'yes': ['yebo', 'y'], 'no': ['cha', 'c']
        }
    },
    'isixhosa': {
        'code': 'xh',
        'name': 'isiXhosa',
        'days': {
            'Monday': 'Mvulo', 'Tuesday': 'Lwesibini', 'Wednesday': 'Lwesithathu',
            'Thursday': 'Lwesine', 'Friday': 'Lwesihlanu', 'Saturday': 'Mgqibelo', 'Sunday': 'Cawe'
        },
        'responses': {
            'welcome': "Wamkelekile kwi-MetaWell AI! Khetha ulwimi: 1.isXhosa 2.English 3.isZulu 4.Afrikaans 5.Sesotho 6.Setswana 7.Sepedi 8.Xitsonga 9.Tshivenda 10.isNdebele 11.siSwati",
            'greeting': "Molo! Bhukisha i-appointment? (Ewe/Hayi)",
            'show_days': "Iintsuku: {days}. Usuku luni?",
            'choose_day': "Kulungile! U-{day}. Ndikhangela iixesha...",
            'show_slots': "Iixesha ku-{day}: {slots}. Ixesha lini?",
            'booking_success': "✅ Iqinisekisiwe! {day} nge-{time}. SMS ithunyelwe!",
            'goodbye': "Enkosi! Sala kakuhle!",
            'yes': ['ewe', 'e'], 'no': ['hayi', 'h']
        }
    },
    'afrikaans': {
        'code': 'af',
        'name': 'Afrikaans',
        'days': {
            'Monday': 'Maandag', 'Tuesday': 'Dinsdag', 'Wednesday': 'Woensdag',
            'Thursday': 'Donderdag', 'Friday': 'Vrydag', 'Saturday': 'Saterdag', 'Sunday': 'Sondag'
        },
        'responses': {
            'welcome': "Welkom by MetaWell AI! Kies taal: 1.Afrikaans 2.English 3.isZulu 4.isXhosa 5.Sesotho 6.Setswana 7.Sepedi 8.Xitsonga 9.Tshivenda 10.isNdebele 11.siSwati",
            'greeting': "Hallo! Maak afspraak? (Ja/Nee)",
            'show_days': "Dae: {days}. Watter dag?",
            'choose_day': "Goed! Jy het {day}. Gaan tye na...",
            'show_slots': "Tye op {day}: {slots}. Watter tyd?",
            'booking_success': "✅ Bevestig! {day} om {time}. SMS gestuur!",
            'goodbye': "Dankie! Totsiens!",
            'yes': ['ja', 'j'], 'no': ['nee', 'n']
        }
    },
    'sesotho': {
        'code': 'st',
        'name': 'Sesotho',
        'days': {
            'Monday': 'Mantaha', 'Tuesday': 'Labobedi', 'Wednesday': 'Laboraro',
            'Thursday': 'Labone', 'Friday': 'Labohlano', 'Saturday': 'Moqebelo', 'Sunday': 'Sontaha'
        },
        'responses': {
            'welcome': "O amohetse ho MetaWell AI! Khetha puo: 1.Sesotho 2.English 3.isZulu 4.isXhosa 5.Afrikaans 6.Setswana 7.Sepedi 8.Xitsonga 9.Tshivenda 10.isNdebele 11.siSwati",
            'greeting': "Lumela! Behanya nako? (Ee/Che)",
            'show_days': "Matsatsi: {days}. Letsatsi life?",
            'choose_day': "Hantle! U {day}. Ke batla lihora...",
            'show_slots': "Lihora ka {day}: {slots}. Nako life?",
            'booking_success': "✅ E netefalitsoe! {day} ka {time}. SMS e rometsoe!",
            'goodbye': "Kea leboha! Sala hantle!",
            'yes': ['ee', 'e'], 'no': ['che', 'c']
        }
    },
    'setswana': {
        'code': 'tn',
        'name': 'Setswana',
        'days': {
            'Monday': 'Mosupologo', 'Tuesday': 'Labobedi', 'Wednesday': 'Laboraro',
            'Thursday': 'Labone', 'Friday': 'Labotlhano', 'Saturday': 'Lamatlhatso', 'Sunday': 'Tshipi'
        },
        'responses': {
            'welcome': "O amogetswe kwa MetaWell AI! Kgetha puo: 1.Setswana 2.English 3.isZulu 4.isXhosa 5.Afrikaans 6.Sesotho 7.Sepedi 8.Xitsonga 9.Tshivenda 10.isNdebele 11.siSwati",
            'greeting': "Dumela! Beakanya nako? (Ee/Nnyaa)",
            'show_days': "Matsatsi: {days}. Letsatsi mang?",
            'choose_day': "Sentle! O {day}. Ke batla dinako...",
            'show_slots': "Dinako ka {day}: {slots}. Nako mang?",
            'booking_success': "✅ E tshotlweetswe! {day} ka {time}. SMS e romilwe!",
            'goodbye': "Ke a leboga! Sala sentle!",
            'yes': ['ee', 'e'], 'no': ['nnyaa', 'n']
        }
    },
    'sepedi': {
        'code': 'nso',
        'name': 'Sepedi',
        'days': {
            'Monday': 'Mošupologo', 'Tuesday': 'Labobedi', 'Wednesday': 'Laboraro',
            'Thursday': 'Labone', 'Friday': 'Labohlano', 'Saturday': 'Mokibelo', 'Sunday': 'Sontaga'
        },
        'responses': {
            'welcome': "O amogetšwe go MetaWell AI! Kgetha polelo: 1.Sepedi 2.English 3.isZulu 4.isXhosa 5.Afrikaans 6.Sesotho 7.Setswana 8.Xitsonga 9.Tshivenda 10.isNdebele 11.siSwati",
            'greeting': "Dumela! Beakanya nako? (Ee/Aowa)",
            'show_days': "Matšatši: {days}. Letšatši lefe?",
            'choose_day': "Gabotse! O {day}. Ke nyaka dinako...",
            'show_slots': "Dinako ka {day}: {slots}. Nako efe?",
            'booking_success': "✅ E tiišeditšwe! {day} ka {time}. SMS e romilwe!",
            'goodbye': "Ke a leboga! Šala gabotse!",
            'yes': ['ee', 'e'], 'no': ['aowa', 'a']
        }
    },
    'xitsonga': {
        'code': 'ts',
        'name': 'Xitsonga',
        'days': {
            'Monday': 'Musumbhunuku', 'Tuesday': 'Ravumbirhi', 'Wednesday': 'Ravurharhu',
            'Thursday': 'Ravumune', 'Friday': 'Ravuntlhanu', 'Saturday': 'Mugqivela', 'Sunday': 'Sonto'
        },
        'responses': {
            'welcome': "U amukeriwe eMetaWell AI! Hlawula ririmi: 1.Xitsonga 2.English 3.isZulu 4.isXhosa 5.Afrikaans 6.Sesotho 7.Setswana 8.Sepedi 9.Tshivenda 10.isNdebele 11.siSwati",
            'greeting': "Avuxeni! Hlayisa nkarhi? (Ina/E-e)",
            'show_days': "Masiku: {days}. Siku rini?",
            'choose_day': "Swi kahle! U {day}. Ndza lava tinako...",
            'show_slots': "Tinako ka {day}: {slots}. Nkarhi rini?",
            'booking_success': "✅ Wu tiyisisiwe! {day} hi {time}. SMS yi rhumeriwe!",
            'goodbye': "Ndza nkhensa! Sala kahle!",
            'yes': ['ina', 'i'], 'no': ['e-e', 'e']
        }
    },
    'tshivenda': {
        'code': 've',
        'name': 'Tshivenda',
        'days': {
            'Monday': 'Musumbuluwo', 'Tuesday': 'Ḽavhuvhili', 'Wednesday': 'Ḽavhuraru',
            'Thursday': 'Ḽavhuṋa', 'Friday': 'Ḽavhuṱanu', 'Saturday': 'Mugivhela', 'Sunday': 'Swondaha'
        },
        'responses': {
            'welcome': "No ambani kha MetaWell AI! Nanga luambo: 1.Tshivenda 2.English 3.isZulu 4.isXhosa 5.Afrikaans 6.Sesotho 7.Setswana 8.Sepedi 9.Xitsonga 10.isNdebele 11.siSwati",
            'greeting': "Ndaa! Bika tshifhinga? (Ee/Aa)",
            'show_days': "Matshili: {days}. Musi?",
            'choose_day': "Zwavhudi! U {day}. Ndi toda tshifhinga...",
            'show_slots': "Tshifhinga kha {day}: {slots}. Tshifhinga tshiani?",
            'booking_success': "✅ Tshi tanganedzwa! {day} tsha {time}. SMS yo rumwa!",
            'goodbye': "Ndi a livhuwa! Sala zwavhudi!",
            'yes': ['ee', 'e'], 'no': ['aa', 'a']
        }
    },
    'isindebele': {
        'code': 'nr',
        'name': 'isiNdebele',
        'days': {
            'Monday': 'Mvulo', 'Tuesday': 'Lwesibili', 'Wednesday': 'Lwesithathu',
            'Thursday': 'Lwesine', 'Friday': 'Lwesihlanu', 'Saturday': 'Mgqibelo', 'Sunday': 'Sonto'
        },
        'responses': {
            'welcome': "Uyamukelwa eMetaWell AI! Khetha ulimi: 1.isNdebele 2.English 3.isZulu 4.isXhosa 5.Afrikaans 6.Sesotho 7.Setswana 8.Sepedi 9.Xitsonga 10.Tshivenda 11.siSwati",
            'greeting': "Salibonani! Bhuka isikhathi? (Yebo/Cha)",
            'show_days': "Izinsuku: {days}. Usuku luni?",
            'choose_day': "Kuhle! U-{day}. Ngibheka izikhathi...",
            'show_slots': "Izikhathi ku-{day}: {slots}. Isikhathi sini?",
            'booking_success': "✅ Siqinisekisiwe! {day} nge-{time}. Izaziso zithunyelwe!",
            'goodbye': "Ngiyabonga! Sala kahle!",
            'yes': ['yebo', 'y'], 'no': ['cha', 'c']
        }
    },
    'siswati': {
        'code': 'ss',
        'name': 'siSwati',
        'days': {
            'Monday': 'Msombuluko', 'Tuesday': 'Lesibili', 'Wednesday': 'Lesitsatfu',
            'Thursday': 'Lesine', 'Friday': 'Lesihlanu', 'Saturday': 'Mgcibelo', 'Sunday': 'Lisontfo'
        },
        'responses': {
            'welcome': "Uyemukelwa eMetaWell AI! Khetsa lulwimi: 1.siSwati 2.English 3.isZulu 4.isXhosa 5.Afrikaans 6.Sesotho 7.Setswana 8.Sepedi 9.Xitsonga 10.Tshivenda 11.isNdebele",
            'greeting': "Sawubona! Bhuka sikhatsi? (Yebo/Cha)",
            'show_days': "Emalanga: {days}. Lilanga liphi?",
            'choose_day': "Kuhle! U {day}. Ngibuka emasikhatsi...",
            'show_slots': "Emasikhatsi nge-{day}: {slots}. Sikhatsi siphi?",
            'booking_success': "✅ Sigcizeleliwe! {day} nge-{time}. SMS itfunyelwe!",
            'goodbye': "Ngiyabonga! Sala kahle!",
            'yes': ['yebo', 'y'], 'no': ['cha', 'c']
        }
    }
}

# Simple language detection based on common words
def detect_language_simple(text):
    text_lower = text.lower()
    
    language_keywords = {
        'isizulu': ['sawubona', 'yebo', 'cha', 'ngiyabonga', 'isikhathi'],
        'isixhosa': ['molo', 'ewe', 'hayi', 'enkosi', 'ixesha'],
        'afrikaans': ['hallo', 'ja', 'nee', 'dankie', 'afspraak'],
        'sesotho': ['dumela', 'ee', 'che', 'kea leboha', 'nako'],
        'setswana': ['dumela', 'ee', 'nnyaa', 'ke a leboga', 'nako'],
        'sepedi': ['dumela', 'ee', 'aowa', 'ke a leboga', 'nako'],
        'xitsonga': ['avuxeni', 'ina', 'e-e', 'ndza nkhensa', 'nkarhi'],
        'tshivenda': ['ndaa', 'ee', 'aa', 'ndi a livhuwa', 'tshifhinga'],
        'isindebele': ['salibonani', 'yebo', 'cha', 'ngiyabonga', 'isikhathi'],
        'siswati': ['sawubona', 'yebo', 'cha', 'ngiyabonga', 'sikhatsi']
    }
    
    for lang, keywords in language_keywords.items():
        if any(keyword in text_lower for keyword in keywords):
            return lang
    
    return 'english'

# Data Storage with Persistence
def load_data():
    try:
        with open('data.json', 'r') as f:
            return json.load(f)
    except:
        return {"patients": {}, "conversations": {}, "bookings": []}

def save_data(data):
    with open('data.json', 'w') as f:
        json.dump(data, f)

# Load existing data
app_data = load_data()
patient_profiles = app_data.get("patients", {})
conversation_states = app_data.get("conversations", {})
all_bookings = app_data.get("bookings", [])

def get_available_days(language='english'):
    """Get next available days in specified language"""
    today = datetime.now()
    available_days = []
    
    for i in range(1, MAX_ADVANCE_DAYS + 1):
        future_date = today + timedelta(days=i)
        day_name_en = future_date.strftime("%A")
        
        if day_name_en in CLINIC_HOURS and CLINIC_HOURS[day_name_en]:
            booked_count = len([b for b in all_bookings 
                              if b.get("day") == day_name_en and b.get("status") == "active"])
            
            if booked_count < MAX_DAILY_SLOTS:
                day_translated = LANGUAGE_CONFIG[language]['days'].get(day_name_en, day_name_en)
                available_days.append(day_translated)
    
    return available_days

def get_available_slots(day_translated, language='english'):
    """Get available slots for a day"""
    # Convert translated day back to English for internal processing
    day_english = day_translated
    for lang_config in LANGUAGE_CONFIG.values():
        for eng_day, trans_day in lang_config['days'].items():
            if trans_day == day_translated:
                day_english = eng_day
                break
    
    if day_english not in CLINIC_HOURS:
        return []
    
    booked_slots = [b["time"] for b in all_bookings 
                   if b.get("day") == day_english and b.get("status") == "active"]
    
    return [slot for slot in CLINIC_HOURS[day_english] if slot not in booked_slots]

def create_booking(patient_phone, day_translated, time, language='english'):
    """Create booking in specified language"""
    # Convert translated day back to English
    day_english = day_translated
    for lang_config in LANGUAGE_CONFIG.values():
        for eng_day, trans_day in lang_config['days'].items():
            if trans_day == day_translated:
                day_english = eng_day
                break
    
    if time not in get_available_slots(day_translated, language):
        return None, "Slot not available"
    
    booking_id = hashlib.md5(f"{patient_phone}{day_english}{time}{datetime.now()}".encode()).hexdigest()
    
    booking = {
        "id": booking_id,
        "patient_phone": patient_phone,
        "day": day_english,
        "time": time,
        "status": "active",
        "timestamp": datetime.now().isoformat(),
        "language": language
    }
    
    all_bookings.append(booking)
    app_data["bookings"] = all_bookings
    save_data(app_data)
    
    return booking, "success"

def send_sms_confirmation(patient_phone, day_translated, time, language='english'):
    """Send SMS in patient's language"""
    messages = {
        'english': f"🏥 MetaWell AI: Confirmed for {day_translated} at {time}",
        'isizulu': f"🏥 MetaWell AI: Siqinisekisiwe ngo-{day_translated} nge-{time}",
        'isixhosa': f"🏥 MetaWell AI: Iqinisekisiwe ku-{day_translated} nge-{time}",
        'afrikaans': f"🏥 MetaWell AI: Bevestig vir {day_translated} om {time}",
        'sesotho': f"🏥 MetaWell AI: E netefalitsoe ka {day_translated} ka {time}",
        'setswana': f"🏥 MetaWell AI: E tshotlweetswe ka {day_translated} ka {time}",
        'sepedi': f"🏥 MetaWell AI: E tiišeditšwe ka {day_translated} ka {time}",
        'xitsonga': f"🏥 MetaWell AI: Wu tiyisisiwe ka {day_translated} hi {time}",
        'tshivenda': f"🏥 MetaWell AI: Tshi tanganedzwa kha {day_translated} tsha {time}",
        'isindebele': f"🏥 MetaWell AI: Siqinisekisiwe ku-{day_translated} nge-{time}",
        'siswati': f"🏥 MetaWell AI: Sigcizeleliwe nge-{day_translated} nge-{time}"
    }
    
    try:
        message = twilio_client.messages.create(
            body=messages.get(language, messages['english']),
            from_=TWILIO_PHONE_NUMBER,
            to=patient_phone
        )
        return message.sid
    except Exception as e:
        print(f"SMS Error: {e}")
        return None

def process_message(message, phone_number):
    msg_lower = message.lower().strip()
    
    if phone_number not in conversation_states:
        conversation_states[phone_number] = {
            'state': 'LANGUAGE_SELECTION',
            'language': 'english'
        }
        app_data["conversations"] = conversation_states
        save_data(app_data)
    
    state_data = conversation_states[phone_number]
    current_state = state_data['state']
    current_language = state_data['language']
    lang_config = LANGUAGE_CONFIG[current_language]
    
    # Language Selection State
    if current_state == 'LANGUAGE_SELECTION':
        # Check for numeric selection (1-11)
        if msg_lower.isdigit() and 1 <= int(msg_lower) <= 11:
            lang_keys = list(LANGUAGE_CONFIG.keys())
            selected_lang = lang_keys[int(msg_lower) - 1]
            state_data['language'] = selected_lang
            state_data['state'] = 'GREETING'
            app_data["conversations"] = conversation_states
            save_data(app_data)
            return LANGUAGE_CONFIG[selected_lang]['responses']['greeting']
        
        # Auto-detect language
        detected_lang = detect_language_simple(message)
        state_data['language'] = detected_lang
        state_data['state'] = 'GREETING'
        app_data["conversations"] = conversation_states
        save_data(app_data)
        return LANGUAGE_CONFIG[detected_lang]['responses']['greeting']
    
    # Greeting State
    elif current_state == 'GREETING':
        yes_words = lang_config['responses']['yes']
        no_words = lang_config['responses']['no']
        
        if any(word in msg_lower for word in yes_words):
            state_data['state'] = 'SHOW_DAYS'
            app_data["conversations"] = conversation_states
            save_data(app_data)
            available_days = get_available_days(current_language)
            days_str = ", ".join(available_days)
            return lang_config['responses']['show_days'].format(days=days_str)
        else:
            conversation_states[phone_number] = {'state': 'LANGUAGE_SELECTION', 'language': 'english'}
            app_data["conversations"] = conversation_states
            save_data(app_data)
            return lang_config['responses']['goodbye']
    
    # Show Available Days
    elif current_state == 'SHOW_DAYS':
        available_days = get_available_days(current_language)
        chosen_day = None
        
        for day in available_days:
            if day.lower() in msg_lower:
                chosen_day = day
                break
        
        if chosen_day:
            state_data['selected_day'] = chosen_day
            state_data['state'] = 'SHOW_SLOTS'
            app_data["conversations"] = conversation_states
            save_data(app_data)
            return lang_config['responses']['choose_day'].format(day=chosen_day)
        else:
            return lang_config['responses']['show_days'].format(days=", ".join(available_days))
    
    # Show Available Time Slots
    elif current_state == 'SHOW_SLOTS':
        chosen_day = state_data.get('selected_day')
        slots = get_available_slots(chosen_day, current_language) if chosen_day else []
        
        if not slots:
            state_data['state'] = 'SHOW_DAYS'
            app_data["conversations"] = conversation_states
            save_data(app_data)
            available_days = get_available_days(current_language)
            return f"No slots on {chosen_day}. Available: {', '.join(available_days)}"
        
        # If this is the first time showing slots, display them
        if 'shown_slots' not in state_data:
            state_data['shown_slots'] = True
            app_data["conversations"] = conversation_states
            save_data(app_data)
            slots_str = ", ".join(slots)
            return lang_config['responses']['show_slots'].format(day=chosen_day, slots=slots_str)
        
        # Process time selection
        chosen_time = None
        for slot in slots:
            if slot.replace(":00", "") in msg_lower or slot in msg_lower:
                chosen_time = slot
                break
        
        if chosen_time:
            booking, status = create_booking(phone_number, chosen_day, chosen_time, current_language)
            if booking:
                send_sms_confirmation(phone_number, chosen_day, chosen_time, current_language)
                conversation_states[phone_number] = {'state': 'LANGUAGE_SELECTION', 'language': 'english'}
                app_data["conversations"] = conversation_states
                save_data(app_data)
                return lang_config['responses']['booking_success'].format(day=chosen_day, time=chosen_time)
            else:
                return "Slot taken. Choose another time."
        else:
            slots_str = ", ".join(slots)
            return lang_config['responses']['show_slots'].format(day=chosen_day, slots=slots_str)
    
    # Default case
    conversation_states[phone_number] = {'state': 'LANGUAGE_SELECTION', 'language': 'english'}
    app_data["conversations"] = conversation_states
    save_data(app_data)
    return LANGUAGE_CONFIG['english']['responses']['welcome']

# Flask Routes
@app.route('/')
def home():
    return "🏥 MetaWell AI - 11 Language Healthcare System - DEPLOYMENT READY"

@app.route('/clinic')
def clinic_dashboard():
    active_bookings = [b for b in all_bookings if b.get("status") == "active"]
    
    stats_html = f"""
    <html>
    <head><title>MetaWell AI Dashboard</title></head>
    <body>
        <h1>🏥 MetaWell AI - 11 Languages Supported</h1>
        <div class="stats">
            <div class="stat-box">Patients: {len(patient_profiles)}</div>
            <div class="stat-box">Active Bookings: {len(active_bookings)}</div>
            <div class="stat-box">Languages: ALL 11 SA Languages</div>
        </div>
        <h2>Recent Bookings:</h2>
        <ul>
    """
    
    for booking in active_bookings[-10:]:
        stats_html += f"<li>{booking.get('day', 'Unknown')} at {booking.get('time', 'Unknown')} - {booking.get('patient_phone', 'Unknown')} ({booking.get('language', 'Unknown')})</li>"
    
    stats_html += "</ul></body></html>"
    return stats_html

@app.route('/whatsapp', methods=['POST'])
def whatsapp_webhook():
    try:
        msg = request.values.get('Body', '').strip()
        from_num = request.values.get('From', '')
        response = process_message(msg, from_num)
        
        xml_response = f'<?xml version="1.0" encoding="UTF-8"?><Response><Message>{response}</Message></Response>'
        return Response(xml_response, mimetype='text/xml')
    except Exception as e:
        print(f"Error: {e}")
        error_xml = '<?xml version="1.0" encoding="UTF-8"?><Response><Message>System error. Please try again.</Message></Response>'
        return Response(error_xml, mimetype='text/xml')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=os.environ.get('PORT', 5000))
