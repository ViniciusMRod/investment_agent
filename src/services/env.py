import os
import yaml

from dotenv import load_dotenv
load_dotenv()  # carrega variáveis do .env quando rodar local

cfg_path = os.getenv("CONFIG_PATH", "./config.yaml")
with open(cfg_path, "r") as f:
    cfg = yaml.safe_load(f)


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

        # Satellite
        self.SAT_ENABLED = os.getenv("SAT_ENABLED", "true").lower() == "true"
        self.SAT_SYMBOLS = [s.strip() for s in os.getenv("SAT_SYMBOLS", "ETH,SOL,BNB").split(",")]
        self.SAT_TIMEFRAME = os.getenv("SAT_TIMEFRAME", "1h")
        self.SAT_SMA_LEN = int(os.getenv("SAT_SMA_LEN", "200"))
        self.SAT_STOP_PCT_MAJORS = float(os.getenv("SAT_STOP_PCT_MAJORS", "0.10"))
        self.SAT_STOP_PCT_ALTS = float(os.getenv("SAT_STOP_PCT_ALTS", "0.12"))
        self.SAT_TP_PARTIAL = float(os.getenv("SAT_TP_PARTIAL", "0.27"))
        self.SAT_TRAIL_PCT = float(os.getenv("SAT_TRAIL_PCT", "0.12"))
        self.SAT_MAX_OPEN_PER_SYMBOL = int(os.getenv("SAT_MAX_OPEN_PER_SYMBOL", "1"))


        # Notifications
        self.TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
        self.TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

        # Misc
        self.KILL_SWITCH_FILE = os.getenv("KILL_SWITCH_FILE", "/app/data/.kill")
        self.TICK_SECONDS = 60

        # Load config.yaml
        cfg_path = os.getenv("CONFIG_PATH", "./config.yaml")
        with open(cfg_path, "r") as f:
            cfg = yaml.safe_load(f)


        self.BASE_ASSET = cfg["symbols"]["base_asset"]
        self.PAIRS = cfg["symbols"]["pairs"]
        self.DB_PATH = cfg["storage"]["db_path"]
        self.TRADES_CSV = cfg["storage"]["trades_csv"]
