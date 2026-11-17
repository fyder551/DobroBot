from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
from app.database.crud import get_event_responses, get_event_by_id
from app.database.db import init_db
import os
import requests
from app.config import VK_TOKEN

app = Flask(__name__)
CORS(app)

# СОЗДАЕМ ТАБЛИЦЫ ПРИ ЗАПУСКЕ (на случай, если база пустая)
with app.app_context():
    try:
        init_db()
        print("✅ Таблицы успешно созданы/проверены в облачной БД")
    except Exception as e:
        print(f"❌ Ошибка инициализации БД: {e}")

@app.route('/')
def index():
    return send_from_directory(os.path.join(os.path.dirname(__file__), 'miniapp'), 'index.html')

@app.route('/api/event/<int:event_id>/users')
def get_users(event_id):
    try:
        event = get_event_by_id(event_id)
        if not event:
            return jsonify({"error": "Event not found"}), 404
            
        responses = get_event_responses(event_id)
        users = []
        
        user_ids = [r.user.vk_id for r in responses if r.user]
        avatars = {}
        
        if user_ids:
            vk_url = f"https://api.vk.com/method/users.get?user_ids={','.join(map(str, user_ids))}&fields=photo_100&access_token={VK_TOKEN}&v=5.199"
            try:
                vk_res = requests.get(vk_url, timeout=5).json()
                avatars = {str(u['id']): u.get('photo_100', '') for u in vk_res.get('response', [])}
            except Exception as e:
                print(f"Ошибка ВК API: {e}")

        for r in responses:
            if r.user:
                name = f"{r.user.first_name} {r.user.last_name or ''}".strip()
                users.append({
                    "id": r.user.vk_id, 
                    "name": name,
                    "avatar": avatars.get(str(r.user.vk_id), "")
                })
                
        return jsonify({
            "title": event.title,
            "max_volunteers": event.max_volunteers,
            "users": users
        })
    except Exception as e:
        print(f"КРИТИЧЕСКАЯ ОШИБКА В API: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)