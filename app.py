from flask import Flask, request, jsonify
import os

app = Flask(__name__)

# Conversation state tracking
conversation_states = {}

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
                return f"Kuhle! Ukhethe u-{day}. Ufuna isikhathi sini? (8, 9, 10, 2, 3)"
        
        return "Angikwazi usuku. Sicela uthi: Msombuluko, Lwesibili, Lwesithathu, njll."
    
    elif current_state == "CHOOSING_TIME":
        if any(word in message_lower for word in ['8', '9', '10', '2', '3']):
            conversation_states[phone_number] = "COMPLETE"
            return "Perfect! 🎉 Isikhathi sakho sihleliwe. Sizohamba kahle!"
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
