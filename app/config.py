import os
from dotenv import load_dotenv

load_dotenv()

VK_TOKEN = os.getenv("VK_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
GROUP_ID = int(os.getenv("GROUP_ID", "0"))
ADMIN_CODE = os.getenv("ADMIN_CODE", "")
ORGANIZER_CODE = os.getenv("ORGANIZER_CODE", "")

if not VK_TOKEN or VK_TOKEN == "placeholder":
    raise ValueError(
        "❌ Токен ВК не найден!\n"
        "Открой файл .env и вставь реальный токен в VK_TOKEN."
    )
