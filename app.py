from flask import Flask, request, jsonify, Response
import os
import hashlib
import json
from datetime import datetime, timedelta
from twilio.rest import Client
from googletrans import Translator
from langdetect import detect

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

# COMPLETE 11 South African Languages Day Mapping
DAY_TRANSLATIONS = {
    'english': {
        'Monday': 'Monday', 'Tuesday': 'Tuesday', 'Wednesday': 'Wednesday',
        'Thursday': 'Thursday', 'Friday': 'Friday', 'Saturday': 'Saturday', 'Sunday': 'Sunday'
    },
    'isizulu': {
        'Monday': 'Msombuluko', 'Tuesday': 'Lwesibili', 'Wednesday': 'Lwesithathu',
        'Thursday': 'Lwesine', 'Friday': 'Lwesihlanu', 'Saturday': 'Mgqibelo', 'Sunday': 'Sonto'
    },
    'isixhosa': {
        'Monday': 'Mvulo', 'Tuesday': 'Lwesibini', 'Wednesday': 'Lwesithathu',
        'Thursday': 'Lwesine', 'Friday': 'Lwesihlanu', 'Saturday': 'Mgqibelo', 'Sunday': 'Cawe'
    },
    'afrikaans': {
        'Monday': 'Maandag', 'Tuesday': 'Dinsdag', 'Wednesday': 'Woensdag',
        'Thursday': 'Donderdag', 'Friday': 'Vrydag', 'Saturday': 'Saterdag', 'Sunday': 'Sondag'
    },
    'sesotho': {
        'Monday': 'Mantaha', 'Tuesday': 'Labobedi', 'Wednesday': 'Laboraro',
        'Thursday': 'Labone', 'Friday': 'Labohlano', 'Saturday': 'Moqebelo', 'Sunday': 'Sontaha'
    },
    'setswana': {
        'Monday': 'Mosupologo', 'Tuesday': 'Labobedi', 'Wednesday': 'Laboraro',
        'Thursday': 'Labone', 'Friday': 'Labotlhano', 'Saturday': 'Lamatlhatso', 'Sunday': 'Tshipi'
    },
    'sepedi': {
        'Monday': 'Mošupologo', 'Tuesday': 'Labobedi', 'Wednesday': 'Laboraro',
        'Thursday': 'Labone', 'Friday': 'Labohlano', 'Saturday': 'Mokibelo', 'Sunday': 'Sontaga'
    },
    'xitsonga': {
        'Monday': 'Musumbhunuku', 'Tuesday': 'Ravumbirhi', 'Wednesday': 'Ravurharhu',
        'Thursday': 'Ravumune', 'Friday': 'Ravuntlhanu', 'Saturday': 'Mugqivela', 'Sunday': 'Sonto'
    },
    'tshivenda': {
        'Monday': 'Musumbuluwo', 'Tuesday': 'Ḽavhuvhili', 'Wednesday': 'Ḽavhuraru',
        'Thursday': 'Ḽavhuṋa', 'Friday': 'Ḽavhuṱanu', 'Saturday': 'Mugivhela', 'Sunday': 'Swondaha'
    },
    'isindebele': {
        'Monday': 'Mvulo', 'Tuesday': 'Lwesibili', 'Wednesday': 'Lwesithathu',
        'Thursday': 'Lwesine', 'Friday': 'Lwesihlanu', 'Saturday': 'Mgqibelo', 'Sunday': 'Sonto'
    },
    'siswati': {
        'Monday': 'Msombuluko', 'Tuesday': 'Lesibili', 'Wednesday': 'Lesitsatfu',
        'Thursday': 'Lesine', 'Friday': 'Lesihlanu', 'Saturday': 'Mgcibelo', 'Sunday': 'Lisontfo'
    }
}

# COMPLETE 11 South African Languages Conversation Texts
CONVERSATION_TEXTS = {
    'english': {
        'welcome': "Welcome to MetaWell AI Clinic! Choose language: 1.English 2.isZulu 3.isXhosa 4.Afrikaans 5.Sesotho 6.Setswana 7.Sepedi 8.Xitsonga 9.Tshivenda 10.isNdebele 11.siSwati",
        'greeting': "Hello! Would you like to book a medical appointment? (Yes/No)",
        'show_days': "Available days: {days}. Which day would you like?",
        'choose_day': "Great! You chose {day}. Checking available times...",
        'show_slots': "Available times on {day}: {slots}. Which time would you like?",
        'no_slots': "No slots available on {day}. Please choose another day: {days}",
        'booking_success': "✅ Appointment confirmed for {day} at {time}. SMS confirmation sent!",
        'goodbye': "Thank you for using MetaWell AI. Goodbye!",
        'yes': 'yes', 'no': 'no'
    },
    'isizulu': {
        'welcome': "Uyemukelwa ku-MetaWell AI! Khetha ulimi: 1.isZulu 2.English 3.isXhosa 4.Afrikaans 5.Sesotho 6.Setswana 7.Sepedi 8.Xitsonga 9.Tshivenda 10.isNdebele 11.siSwati",
        'greeting': "Sawubona! Ingabe ufuna ukubhuka isikhathi soku vakasha? (Yebo/Cha)",
        'show_days': "Izinsuku ezitholakalayo: {days}. Ufuna usuku luni?",
        'choose_day': "Kuhle! Ukhethe u-{day}. Ngibheka izikhathi...",
        'show_slots': "Izikhathi ku-{day}: {slots}. Ufuna isikhathi sini?",
        'no_slots': "Azikho izikhathi ku-{day}. Khetha olunye usuku: {days}",
        'booking_success': "✅ Isikhathi sakho siqinisekisiwe ku-{day} nge-{time}. I-SMS isithunyelwe!",
        'goodbye': "Ngiyabonga! Sala kahle!",
        'yes': 'yebo', 'no': 'cha'
    },
    'isixhosa': {
        'welcome': "Wamkelekile kwi-MetaWell AI! Khetha ulwimi: 1.isXhosa 2.English 3.isZulu 4.Afrikaans 5.Sesotho 6.Setswana 7.Sepedi 8.Xitsonga 9.Tshivenda 10.isNdebele 11.siSwati",
        'greeting': "Molo! Ingaba ufuna ukubhukisha i-appointment? (Ewe/Hayi)",
        'show_days': "Iintsuku ezikhoyo: {days}. Ufuna usuku luni?",
        'choose_day': "Kulungile! Ukhethe u-{day}. Ndiyakhangela iixesha...",
        'show_slots': "Iixesha ku-{day}: {slots}. Ufuna ixesha lini?",
        'no_slots': "Azikho iixesha ku-{day}. Khetha enye intsuku: {days}",
        'booking_success': "✅ I-appointment yakho iqinisekisiwe ku-{day} nge-{time}. I-SMS ithunyelwe!",
        'goodbye': "Enkosi! Sala kakuhle!",
        'yes': 'ewe', 'no': 'hayi'
    },
    'afrikaans': {
        'welcome': "Welkom by MetaWell AI! Kies taal: 1.Afrikaans 2.English 3.isZulu 4.isXhosa 5.Sesotho 6.Setswana 7.Sepedi 8.Xitsonga 9.Tshivenda 10.isNdebele 11.siSwati",
        'greeting': "Hallo! Wil jy 'n afspraak maak? (Ja/Nee)",
        'show_days': "Beskikbare dae: {days}. Watter dag verkies jy?",
        'choose_day': "Goed! Jy het {day} gekies. Gaan tye na...",
        'show_slots': "Beskikbare tye op {day}: {slots}. Watter tyd verkies jy?",
        'no_slots': "Geen tye op {day}. Kies ander dag: {days}",
        'booking_success': "✅ Afspraak bevestig vir {day} om {time}. SMS gestuur!",
        'goodbye': "Dankie! Totsiens!",
        'yes': 'ja', 'no': 'nee'
    },
    'sesotho': {
        'welcome': "O amohetswe ho MetaWell AI! Khetha puo: 1.Sesotho 2.English 3.isZulu 4.isXhosa 5.Afrikaans 6.Setswana 7.Sepedi 8.Xitsonga 9.Tshivenda 10.isNdebele 11.siSwati",
        'greeting': "Dumela! Na o batla ho beha nako ya kalafo? (Ee/Che)",
        'show_days': "Matsatsi a fumanehang: {days}. O batla letsatsi lefe?",
        'choose_day': "Hantle! O khethe {day}. Ke batla hora...",
        'show_slots': "Hora ke {day}: {slots}. Ka nako efe?",
        'no_slots': "Ha ho hora {day}. Khetha letsatsi le leng: {days}",
        'booking_success': "✅ Nako ya hao e netefaditswe ka {day} ka {time}. SMS e rometswe!",
        'goodbye': "Kea leboha! Sala hantle!",
        'yes': 'ee', 'no': 'che'
    },
    'setswana': {
        'welcome': "O amogetswe kwa MetaWell AI! Kgetha puo: 1.Setswana 2.English 3.isZulu 4.isXhosa 5.Afrikaans 6.Sesotho 7.Sepedi 8.Xitsonga 9.Tshivenda 10.isNdebele 11.siSwati",
        'greeting': "Dumela! A o batla go beakanya nako ya kalafi? (Ee/Nnyaa)",
        'show_days': "Matsatsi a a leng teng: {days}. O batla letsatsi mang?",
        'choose_day': "Sentle! O kgethile {day}. Ke batla dinako...",
        'show_slots': "Dinako ka {day}: {slots}. O batla nako mang?",
        'no_slots': "Ga go dinako ka {day}. Kgetha letsatsi le lengwe: {days}",
        'booking_success': "✅ Nako ya gago e tshotlweetswe ka {day} ka {time}. SMS e romilwe!",
        'goodbye': "Ke a leboga! Sala sentle!",
        'yes': 'ee', 'no': 'nnyaa'
    },
    'sepedi': {
        'welcome': "O amogetšwe go MetaWell AI! Kgetha polelo: 1.Sepedi 2.English 3.isZulu 4.isXhosa 5.Afrikaans 6.Sesotho 7.Setswana 8.Xitsonga 9.Tshivenda 10.isNdebele 11.siSwati",
        'greeting': "Dumela! Na o nyaka go beakanya nako ya kalafo? (Ee/Aowa)",
        'show_days': "Matšatši a a lego gona: {days}. O nyaka letšatši lefe?",
        'choose_day': "Gabotse! O kgethile {day}. Ke nyaka dinako...",
        'show_slots': "Dinako ka {day}: {slots}. O nyaka nako efe?",
        'no_slots': "Ga go na dinako ka {day}. Kgetha letšatši le lengwe: {days}",
        'booking_success': "✅ Nako ya gago e tiišeditšwe ka {day} ka {time}. SMS e romilwe!",
        'goodbye': "Ke a leboga! Šala gabotse!",
        'yes': 'ee', 'no': 'aowa'
    },
    'xitsonga': {
        'welcome': "U amukeriwe eMetaWell AI! Hlawula ririmi: 1.Xitsonga 2.English 3.isZulu 4.isXhosa 5.Afrikaans 6.Sesotho 7.Setswana 8.Sepedi 9.Tshivenda 10.isNdebele 11.siSwati",
        'greeting': "Avuxeni! Xana u lava ku hlayisa nkarhi wa vuswikoti? (Ina/E-e)",
        'show_days': "Masiku ya ku kuma: {days}. U lava siku rini?",
        'choose_day': "Swi kahle! U hlawule {day}. Ndza lava tinako...",
        'show_slots': "Tinako ka {day}: {slots}. U lava nkarhi rini?",
        'no_slots': "A ku na tinako ka {day}. Hlawula sin'wana siku: {days}",
        'booking_success': "✅ Nkarhi wa wena wu tiyisisiwe ka {day} hi {time}. SMS yi rhumeriwe!",
        'goodbye': "Ndza nkhensa! Sala kahle!",
        'yes': 'ina', 'no': 'e-e'
    },
    'tshivenda': {
        'welcome': "No ambani kha MetaWell AI! Nanga luambo: 1.Tshivenda 2.English 3.isZulu 4.isXhosa 5.Afrikaans 6.Sesotho 7.Setswana 8.Sepedi 9.Xitsonga 10.isNdebele 11.siSwati",
        'greeting': "Ndaa! Naa u toda u bika tshifhinga tsha vhulapfu? (Ee/Aa)",
        'show_days': "Matshili a wanala: {days}. U toda musi?",
        'choose_day': "Zwavhudi! U nanga {day}. Ndi toda tshifhinga...",
        'show_slots': "Tshifhinga kha {day}: {slots}. U toda tshifhinga tshiani?",
        'no_slots': "A hu na tshifhinga kha {day}. Nanga linwe musi: {days}",
        'booking_success': "✅ Tshifhinga tshawe tshi tanganedzwa kha {day} tsha {time}. SMS yo rumwa!",
        'goodbye': "Ndi a livhuwa! Sala zwavhudi!",
        'yes': 'ee', 'no': 'aa'
    },
    'isindebele': {
        'welcome': "Uyamukelwa eMetaWell AI! Khetha ulimi: 1.isNdebele 2.English 3.isZulu 4.isXhosa 5.Afrikaans 6.Sesotho 7.Setswana 8.Sepedi 9.Xitsonga 10.Tshivenda 11.siSwati",
        'greeting': "Salibonani! Ingabe ufuna ukubhuka isikhathi sokwelapha? (Yebo/Cha)",
        'show_days': "Izinsuku ezitholakalayo: {days}. Ufuna usuku luni?",
        'choose_day': "Kuhle! Ukhethe u-{day}. Ngibheka izikhathi...",
        'show_slots': "Izikhathi ku-{day}: {slots}. Ufuna isikhathi sini?",
        'no_slots': "Azikho izikhathi ku-{day}. Khetha olunye usuku: {days}",
        'booking_success': "✅ Isikhathi sakho siqinisekisiwe ku-{day} nge-{time}. Izaziso zithunyelwe!",
        'goodbye': "Ngiyabonga! Sala kahle!",
        'yes': 'yebo', 'no': 'cha'
    },
    'siswati': {
        'welcome': "Uyemukelwa eMetaWell AI! Khetsa lulwimi: 1.siSwati 2.English 3.isZulu 4.isXhosa 5.Afrikaans 6.Sesotho 7.Setswana 8.Sepedi 9.Xitsonga 10.Tshivenda 11.isNdebele",
        'greeting': "Sawubona! Ingabe ufuna kubhuka sikhatsi sekwelapha? (Yebo/Cha)",
        'show_days': "Emalanga lakhona: {days}. Ufuna lilanga liphi?",
        'choose_day': "Kuhle! Ukhetse {day}. Ngibuka emasikhatsi...",
        'show_slots': "Emasikhatsi nge-{day}: {slots}. Ufuna sikhatsi siphi?",
        'no_slots': "Awunawo emasikhatsi nge-{day}. Khetsa lilanga lelilodza: {days}",
        'booking_success': "✅ Sikhatsi sakho sigcizeleliwe nge-{day} nge-{time}. SMS itfunyelwe!",
        'goodbye': "Ngiyabonga! Sala kahle!",
        'yes': 'yebo', 'no': 'cha'
    }
}

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
translator = Translator()

def detect_language(text):
    """Detect input language"""
    try:
        lang_code = detect(text)
        # Map language codes to our language keys
        lang_map = {
            'en': 'english', 'zu': 'isizulu', 'xh': 'isixhosa', 'af': 'afrikaans',
            'st': 'sesotho', 'tn': 'setswana', 'nso': 'sepedi', 'ts': 'xitsonga',
            've': 'tshivenda', 'nr': 'isindebele', 'ss': 'siswati'
        }
        return lang_map.get(lang_code, 'english')
    except:
        return 'english'

def get_available_days(language='english'):
    """Get next available days in specified language"""
    today = datetime.now()
    available_days = []
    
    for i in range(1, MAX_ADVANCE_DAYS + 1):
        future_date = today + timedelta(days=i)
        day_name_en = future_date.strftime("%A")
        
        if day_name_en in CLINIC_HOURS and CLINIC_HOURS[day_name_en]:
            booked_count = len([b for b in all_bookings 
                              if b["day"] == day_name_en and b["status"] == "active"])
            
            if booked_count < MAX_DAILY_SLOTS:
                day_translated = DAY_TRANSLATIONS[language].get(day_name_en, day_name_en)
                available_days.append(day_translated)
    
    return available_days

def get_available_slots(day_translated, language='english'):
    """Get available slots for a day"""
    # Convert translated day back to English for internal processing
    day_english = day_translated
    for lang, days in DAY_TRANSLATIONS.items():
        for eng_day, trans_day in days.items():
            if trans_day == day_translated:
                day_english = eng_day
                break
    
    if day_english not in CLINIC_HOURS:
        return []
    
    booked_slots = [b["time"] for b in all_bookings 
                   if b["day"] == day_english and b["status"] == "active"]
    
    return [slot for slot in CLINIC_HOURS[day_english] if slot not in booked_slots]

def create_booking(patient_phone, day_translated, time, language='english'):
    """Create booking in specified language"""
    # Convert translated day back to English
    day_english = day_translated
    for lang, days in DAY_TRANSLATIONS.items():
        for eng_day, trans_day in days.items():
            if trans_day == day_translated:
                day_english = eng_day
                break
    
    if time not in get_available_slots(day_translated, language):
        return None, CONVERSATION_TEXTS[language]['no_slots'].format(day=day_translated, days=", ".join(get_available_days(language)))
    
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
    save_data()
    
    return booking, "success"

def send_sms_confirmation(patient_phone, day_translated, time, language='english'):
    """Send SMS in patient's language"""
    messages = {
        'english': f"🏥 MetaWell AI: Appointment confirmed for {day_translated} at {time}.",
        'isizulu': f"🏥 MetaWell AI: Isikhathi sakho siqinisekisiwe ngo-{day_translated} nge-{time}.",
        'isixhosa': f"🏥 MetaWell AI: I-appointment yakho iqinisekisiwe ku-{day_translated} nge-{time}.",
        'afrikaans': f"🏥 MetaWell AI: Afspraak bevestig vir {day_translated} om {time}.",
        'sesotho': f"🏥 MetaWell AI: Nako ea hau e netefalitsoe ka {day_translated} ka {time}.",
        'setswana': f"🏥 MetaWell AI: Nako ya gago e tshotlweetswe ka {day_translated} ka {time}.",
        'sepedi': f"🏥 MetaWell AI: Nako ya gago e tiišeditšwe ka {day_translated} ka {time}.",
        'xitsonga': f"🏥 MetaWell AI: Nkarhi wa wena wu tiyisisiwe ka {day_translated} hi {time}.",
        'tshivenda': f"🏥 MetaWell AI: Tshifhinga tshawe tshi tanganedzwa kha {day_translated} tsha {time}.",
        'isindebele': f"🏥 MetaWell AI: Isikhathi sakho siqinisekisiwe ku-{day_translated} nge-{time}.",
        'siswati': f"🏥 MetaWell AI: Sikhatsi sakho sigcizeleliwe nge-{day_translated} nge-{time}."
    }
    
    try:
        message = twilio_client.messages.create(
            body=messages.get(language, messages['english']),
            from_=TWILIO_PHONE_NUMBER,
            to=patient_phone
        )
        return message.sid
    except:
        return None

def process_message(message, phone_number):
    msg_lower = message.lower().strip()
    
    if phone_number not in conversation_states:
        conversation_states[phone_number] = {
            'state': 'LANGUAGE_SELECTION',
            'language': 'english'
        }
    
    state_data = conversation_states[phone_number]
    current_state = state_data['state']
    current_language = state_data['language']
    
    # Language Selection State
    if current_state == 'LANGUAGE_SELECTION':
        # Check for numeric selection (1-11)
        if msg_lower.isdigit() and 1 <= int(msg_lower) <= 11:
            lang_keys = list(CONVERSATION_TEXTS.keys())
            selected_lang = lang_keys[int(msg_lower) - 1]
            state_data['language'] = selected_lang
            state_data['state'] = 'GREETING'
            save_data()
            return CONVERSATION_TEXTS[selected_lang]['greeting']
        
        # Check for language name in message
        for lang_key in CONVERSATION_TEXTS.keys():
            if lang_key in msg_lower or CONVERSATION_TEXTS[lang_key]['yes'].split('/')[0] in msg_lower:
                state_data['language'] = lang_key
                state_data['state'] = 'GREETING'
                save_data()
                return CONVERSATION_TEXTS[lang_key]['greeting']
        
        # Auto-detect language
        detected_lang = detect_language(message)
        state_data['language'] = detected_lang
        state_data['state'] = 'GREETING'
        save_data()
        return CONVERSATION_TEXTS[detected_lang]['greeting']
    
    # Greeting State
    elif current_state == 'GREETING':
        yes_words = CONVERSATION_TEXTS[current_language]['yes'].split('/')
        no_words = CONVERSATION_TEXTS[current_language]['no'].split('/')
        
        if any(word in msg_lower for word in yes_words):
            state_data['state'] = 'SHOW_DAYS'
            save_data()
            available_days = get_available_days(current_language)
            days_str = ", ".join(available_days)
            return CONVERSATION_TEXTS[current_language]['show_days'].format(days=days_str)
        else:
            conversation_states[phone_number] = {'state': 'LANGUAGE_SELECTION', 'language': 'english'}
            save_data()
            return CONVERSATION_TEXTS[current_language]['goodbye']
    
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
            save_data()
            return CONVERSATION_TEXTS[current_language]['choose_day'].format(day=chosen_day)
        else:
            return CONVERSATION_TEXTS[current_language]['show_days'].format(days=", ".join(available_days))
    
    # Show Available Time Slots
    elif current_state == 'SHOW_SLOTS':
        chosen_day = state_data.get('selected_day')
        slots = get_available_slots(chosen_day, current_language) if chosen_day else []
        
        if not slots:
            state_data['state'] = 'SHOW_DAYS'
            save_data()
            available_days = get_available_days(current_language)
            return CONVERSATION_TEXTS[current_language]['no_slots'].format(day=chosen_day, days=", ".join(available_days))
        
        # If this is the first time showing slots, display them
        if 'shown_slots' not in state_data:
            state_data['shown_slots'] = True
            save_data()
            slots_str = ", ".join(slots)
            return CONVERSATION_TEXTS[current_language]['show_slots'].format(day=chosen_day, slots=slots_str)
        
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
                save_data()
                return CONVERSATION_TEXTS[current_language]['booking_success'].format(day=chosen_day, time=chosen_time)
            else:
                return status
        else:
            slots_str = ", ".join(slots)
            return CONVERSATION_TEXTS[current_language]['show_slots'].format(day=chosen_day, slots=slots_str)
    
    # Default case
    conversation_states[phone_number] = {'state': 'LANGUAGE_SELECTION', 'language': 'english'}
    save_data()
    return CONVERSATION_TEXTS['english']['welcome']

# Flask Routes (REMAIN THE SAME)
@app.route('/')
def home():
    return "🏥 MetaWell AI Multilingual Healthcare System - ALL 11 LANGUAGES SUPPORT"

@app.route('/clinic')
def clinic_dashboard():
    active_bookings = [b for b in all_bookings if b["status"] == "active"]
    
    stats_html = f"""
    <html>
    <head><title>MetaWell AI Dashboard</title></head>
    <body>
        <h1>🏥 MetaWell AI Clinic Dashboard</h1>
        <div class="stats">
            <div class="stat-box">Patients: {len(patient_profiles)}</div>
            <div class="stat-box">Active Bookings: {len(active_bookings)}</div>
            <div class="stat-box">Languages: ALL 11 SA Languages</div>
        </div>
        <h2>Recent Bookings:</h2>
        <ul>
    """
    
    for booking in active_bookings[-10:]:
        stats_html += f"<li>{booking['day']} at {booking['time']} - {booking['patient_phone']} ({booking['language']})</li>"
    
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
        error_xml = '<?xml version="1.0" encoding="UTF-8"?><Response><Message>System error. Please try again.</Message></Response>'
        return Response(error_xml, mimetype='text/xml')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=os.environ.get('PORT', 5000))
