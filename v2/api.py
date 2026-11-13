from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
from app.database.crud import get_event_responses, get_event_by_id
import os

app = Flask(__name__)
CORS(app)

@app.route('/')
def index():
    # Теперь папка miniapp лежит прямо рядом с api.py
    return send_from_directory(os.path.join(os.path.dirname(__file__), 'miniapp'), 'index.html')

@app.route('/api/event/<int:event_id>/users')
def get_users(event_id):
    event = get_event_by_id(event_id)
    if not event:
        return jsonify({"error": "Event not found"}), 404
        
    responses = get_event_responses(event_id)
    users = []
    
    for r in responses:
        if r.user:
            name = f"{r.user.first_name} {r.user.last_name or ''}".strip()
            users.append({"id": r.user.vk_id, "name": name})
            
    return jsonify({
        "title": event.title,
        "max_volunteers": event.max_volunteers,
        "users": users
    })

if __name__ == '__main__':
    # Render сам передаст нужный порт в переменную PORT
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)