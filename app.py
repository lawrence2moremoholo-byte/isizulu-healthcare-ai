from flask import Flask, request, jsonify
import os

app = Flask(__name__)

@app.route('/')
def home():
    return "🏥 IsiZulu Healthcare AI is LIVE!"

@app.route('/health')
def health_check():
    return jsonify({"status": "healthy", "service": "isizulu_healthcare"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=os.environ.get('PORT', 5000))
