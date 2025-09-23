from flask import Flask, request, jsonify
import os
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

app = Flask(__name__)

# Your AI model setup (simplified for now)
def load_model():
    # This will be your trained model - for now basic responses
    return "model_loaded"

model = load_model()

@app.route('/')
def home():
    return "🏥 IsiZulu Healthcare AI is LIVE!"

@app.route('/health')
def health_check():
    return jsonify({"status": "healthy", "service": "isizulu_healthcare"})

# WHATSAPP WEBHOOK - THIS IS CRITICAL
@app.route('/whatsapp', methods=['POST'])
def whatsapp_webhook():
    try:
        # Get incoming WhatsApp message
        incoming_msg = request.values.get('Body', '').strip()
        from_number = request.values.get('From', '')
        
        print(f"Received message from {from_number}: {incoming_msg}")
        
        # Process message with your AI
        response_text = process_message(incoming_msg)
        
        # Return WhatsApp-compatible response
        return f'<Response><Message>{response_text}</Message></Response>'
        
    except Exception as e:
        print(f"Error: {e}")
        return f'<Response><Message>Ngiyaxolisa, iphutha lifikile. Ngicela uzame futhi.</Message></Response>'

def process_message(message):
    """Your AI message processing logic"""
    message_lower = message.lower()
    
    # Basic intent detection
    if any(word in message_lower for word in ['sawubona', 'hello', 'hi']):
        return "Sawubona! 🏥 Ngingakusiza kanjani ngokubuka udokotela?"
    
    elif any(word in message_lower for word in ['isikhathi', 'appointment', 'udokotela', 'doctor']):
        return "Kuhle! Ufuna ukubona udokotela? Ufuna usuku luni? (Msombuluko, Lwesibili, Lwesithathu, njll)"
    
    elif any(word in message_lower for word in ['msombuluko', 'monday']):
        return "Kuhle! Ukhethe uMsombuluko. Ufuna isikhathi sini? (8, 9, 10, 2, 3)"
    
    elif any(word in message_lower for word in ['8', '9', '10', '2', '3']):
        return "Perfect! Isikhathi sakho sihleliwe. Sizohamba kahle! 🎉"
    
    else:
        return "Sawubona! Ngingakusiza kanjani ngokubuka udokotela? (Faka usuku noma isikhathi)"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=os.environ.get('PORT', 5000))
