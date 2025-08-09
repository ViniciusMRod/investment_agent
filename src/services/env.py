import os
import yaml

class Env:
    def __init__(self):
        # .env via docker-compose
        self.TESTNET = os.getenv("TESTNET", "true").lower() == "true"
        self.LIVE = os.getenv("LIVE", "false").lower() == "true"
        self.API_KEY = os.getenv("BINANCE_API_KEY", "")
        self.API_SECRET = os.getenv("BINANCE_API_SECRET", "")

        # Targets
        self.TARGETS = {
            "BTC": float(os.getenv("TARGET_BTC", "0.60")),
            "ETH": float(os.getenv("TARGET_ETH", "0.25")),
            "SOL": float(os.getenv("TARGET_SOL", "0.10")),
            "BNB": float(os.getenv("TARGET_BNB", "0.05")),
        }

        # DCA
        self.DCA_ENABLED = os.getenv("DCA_ENABLED", "true").lower() == "true"
        self.DCA_DAY = int(os.getenv("DCA_DAY", "5"))
        self.DCA_AMOUNT_BASE = float(os.getenv("DCA_AMOUNT_BASE", "50.0"))
        self.DCA_BASE_ASSET = os.getenv("DCA_BASE_ASSET", "EUR")
        self.DCA_SYMBOLS = [s.strip() for s in os.getenv("DCA_SYMBOLS", "BTC,ETH,SOL,BNB").split(",")]

        # Rebalance
        self.REBALANCE_ENABLED = os.getenv("REBALANCE_ENABLED", "true").lower() == "true"
        self.REBALANCE_WEEKDAY = int(os.getenv("REBALANCE_WEEKDAY", "2"))
        self.REBALANCE_TOLERANCE = float(os.getenv("REBALANCE_TOLERANCE", "0.05"))

        # Risk
        self.DAILY_LOSS_CAP_PCT = float(os.getenv("DAILY_LOSS_CAP_PCT", "0.015"))
        self.MAX_ORDERS_PER_DAY = int(os.getenv("MAX_ORDERS_PER_DAY", "20"))
        self.RISK_PER_TRADE = float(os.getenv("RISK_PER_TRADE", "0.01"))

        # Notifications
        self.TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
        self.TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

        # Misc
        self.KILL_SWITCH_FILE = os.getenv("KILL_SWITCH_FILE", "/app/data/.kill")
        self.TICK_SECONDS = 60

        # Load config.yaml
        with open("/app/config.yaml", "r") as f:
            cfg = yaml.safe_load(f)

        self.BASE_ASSET = cfg["symbols"]["base_asset"]
        self.PAIRS = cfg["symbols"]["pairs"]
        self.DB_PATH = cfg["storage"]["db_path"]
        self.TRADES_CSV = cfg["storage"]["trades_csv"]
