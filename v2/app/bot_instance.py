import truststore
truststore.inject_into_ssl()

import logging
from vkbottle.bot import Bot
from app.config import VK_TOKEN

logging.getLogger("vkbottle").setLevel(logging.WARNING)

bot = Bot(token=VK_TOKEN)