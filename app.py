from flask import Flask, request, jsonify
import os

app = Flask(__name__)

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
        
        print("Received: " + str(incoming_msg))
        
        response_text = process_message(incoming_msg)
        
        return f'<Response><Message>{response_text}</Message></Response>'
        
    except Exception as e:
        return f'<Response><Message>Error occurred. Please try again.</Message></Response>'

def process_message(message):
    message_lower = message.lower()
    
    if any(word in message_lower for word in ['sawubona', 'hello', 'hi']):
        return "Sawubona! 🏥 Ngingakusiza kanjani ngokubuka udokotela?"
    
    elif any(word in message_lower for word in ['isikhathi', 'appointment', 'udokotela', 'doctor']):
        return "Kuhle! Ufuna ukubona udokotela? Ufuna usuku luni? (Msombuluko, Lwesibili, Lwesithathu, njll)"
    
    elif any(word in message_lower for word in ['msombuluko', 'monday', 'lwesibili', 'tuesday']):
        return "Kuhle! Ukhethe uMsombuluko. Ufuna isikhathi sini? (8, 9, 10, 2, 3)"
    
    elif any(word in message_lower for word in ['8', '9', '10', '2', '3']):
        return "Perfect! Isikhathi sakho sihleliwe. Sizohamba kahle! 🎉"
    
    else:
        return "Sawubona! Ngingakusiza kanjani ngokubuka udokotela?"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=os.environ.get('PORT', 5000))
