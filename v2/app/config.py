import os
from dotenv import load_dotenv

# Загружаем .env из корня папки v2
load_dotenv()

VK_TOKEN = os.getenv("VK_TOKEN")
GROUP_ID = int(os.getenv("GROUP_ID", "0")) # 67512708
CHAT_ID = int(os.getenv("CHAT_ID", "0"))