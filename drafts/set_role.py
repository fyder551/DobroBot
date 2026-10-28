import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.database.db import get_session
from app.database.models import User

VK_ID = 455965497  # ваш VK ID
NEW_ROLE = "admin"  # или "organizer"

session = get_session()
user = session.query(User).filter_by(vk_id=VK_ID).first()

if user:
    user.role = NEW_ROLE
    session.commit()
    print(f"✅ Роль пользователя {user.full_name} изменена на '{NEW_ROLE}'")
else:
    print("❌ Пользователь не найден")

session.close()