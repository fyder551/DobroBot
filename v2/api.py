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
    
    # Собираем ID всех участников для запроса аватарок
    user_ids = [r.user.vk_id for r in responses if r.user]
    avatars = {}
    
    if user_ids:
        import requests
        from app.config import VK_TOKEN
        # Запрашиваем аватарки (photo_100) одним запросом к ВК
        vk_url = f"https://api.vk.com/method/users.get?user_ids={','.join(map(str, user_ids))}&fields=photo_100&access_token={VK_TOKEN}&v=5.199"
        try:
            vk_res = requests.get(vk_url).json()
            avatars = {str(u['id']): u.get('photo_100', '') for u in vk_res.get('response', [])}
        except Exception as e:
            print(f"Ошибка получения аватарок: {e}")

    for r in responses:
        if r.user:
            name = f"{r.user.first_name} {r.user.last_name or ''}".strip()
            users.append({
                "id": r.user.vk_id, # ID профиля нужен для ссылки
                "name": name,
                "avatar": avatars.get(str(r.user.vk_id), "")
            })
            
    return jsonify({
        "title": event.title,
        "max_volunteers": event.max_volunteers,
        "users": users
    })