from binance.spot import Spot as Client
from binance.error import ClientError
import time
from .logger import get_logger

log = get_logger()

class Exchange:
    def __init__(self, env):
        self.env = env
        base_url = "https://testnet.binance.vision" if env.TESTNET else None
        self.client = Client(api_key=env.API_KEY, api_secret=env.API_SECRET, base_url=base_url)
        self.recv_window = 10000  # 10s de tolerância
        self._last_server_ms = 0
        self._last_sync = 0.0
        self._sync_interval = 300  # 5min

        # sincroniza uma vez
        self._sync_time(hard=True)

    # ---------- time helpers ----------
    def _server_ms(self) -> int:
        now = time.time()
        if now - self._last_sync > self._sync_interval or self._last_server_ms == 0:
            self._sync_time()
        return int(self._last_server_ms)

    def _sync_time(self, hard=False):
        data = self.client.time()  # GET /api/v3/time (público)
        self._last_server_ms = int(data["serverTime"])
        self._last_sync = time.time()
        if hard:
            log.info("Time sync init: serverTime=%d", self._last_server_ms)

    # ---------- public ----------
    def price(self, symbol):
        data = self.client.ticker_price(symbol)
        return float(data["price"])

    # ---------- private with server timestamp + retry ----------
    def _with_retry_1021(self, fn, *args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except ClientError as e:
            if isinstance(e.args, tuple) and len(e.args) >= 2 and e.args[1] == -1021:
                # re-sincroniza e tenta 1x
                log.warning("Binance -1021: re-sync and retry once")
                self._sync_time(hard=True)
                kwargs["timestamp"] = self._server_ms()
                return fn(*args, **kwargs)
            raise

    def account_balances(self):
        params = dict(recvWindow=self.recv_window, timestamp=self._server_ms())
        acc = self._with_retry_1021(self.client.account, **params)
        return {b["asset"]: float(b["free"]) + float(b["locked"]) for b in acc["balances"]}

    def order_market(self, symbol, side, quote_order_qty=None, quantity=None):
        params = dict(symbol=symbol, side=side, type="MARKET",
                      recvWindow=self.recv_window, timestamp=self._server_ms())
        if quote_order_qty is not None:
            params["quoteOrderQty"] = str(quote_order_qty)
        else:
            params["quantity"] = str(quantity)
        return self._with_retry_1021(self.client.new_order, **params)

    def order_limit(self, symbol, side, quantity, price, tif="GTC"):
        params = dict(symbol=symbol, side=side, type="LIMIT", timeInForce=tif,
                      quantity=str(quantity), price=str(price),
                      recvWindow=self.recv_window, timestamp=self._server_ms())
        return self._with_retry_1021(self.client.new_order, **params)

    def exchange_info(self, symbol):
        return self.client.exchange_info(symbol=symbol)
