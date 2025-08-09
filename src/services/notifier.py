from .logger import get_logger
import os

log = get_logger()

class Notifier:
    def __init__(self, env):
        self.env = env
        self.enabled = bool(env.TELEGRAM_BOT_TOKEN and env.TELEGRAM_CHAT_ID)
        if self.enabled:
            try:
                from telegram import Bot
                self.bot = Bot(token=env.TELEGRAM_BOT_TOKEN)
            except Exception as e:
                log.warning("Telegram indisponível: %s", e)
                self.enabled = False

    def safe_send(self, msg: str):
        if not self.enabled:
            log.info("NOTIFY: %s", msg)
            return
        try:
            self.bot.send_message(chat_id=self.env.TELEGRAM_CHAT_ID, text=msg)
        except Exception as e:
            log.warning("Falha envio Telegram: %s", e)
