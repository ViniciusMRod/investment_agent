from binance.spot import Spot as Client
import time
from .logger import get_logger

log = get_logger()

class Exchange:
    def __init__(self, env):
        self.env = env
        base_url = "https://testnet.binance.vision" if env.TESTNET else None
        self.client = Client(api_key=env.API_KEY, api_secret=env.API_SECRET, base_url=base_url)

        # tolerância de tempo da API
        self.recv_window = 5000  # 5s

        # controle de skew com o serverTime
        self._last_sync_ts = 0.0
        self._skew_ms = 0  # server_time_ms - local_time_ms
        self._sync_interval_sec = 600  # revalidar a cada 10min
        try:
            self._sync_time()
        except Exception as e:
            log.warning("Falha ao sincronizar serverTime na inicialização: %s", e)

    # ---------- Time sync ----------
    def _now_ms(self) -> int:
        return int(time.time() * 1000)

    def _sync_time(self):
        server_time_ms = int(self.client.time()["serverTime"])
        local_ms = self._now_ms()
        self._skew_ms = server_time_ms - local_ms
        self._last_sync_ts = time.time()
        log.info("Time sync: skew=%d ms (server-local)", self._skew_ms)

    def _maybe_wait_if_ahead(self):
        """
        Se o relógio local estiver adiantado (skew_ms < 0), espera até alinhar.
        Re-sincroniza a cada _sync_interval_sec.
        """
        # revalida periodicamente
        if time.time() - self._last_sync_ts > self._sync_interval_sec:
            try:
                self._sync_time()
            except Exception as e:
                log.warning("Falha ao re-sincronizar serverTime: %s", e)

        # se local está à frente do server, aguarda
        if self._skew_ms < -50:  # margem de 50ms
            wait_ms = -self._skew_ms
            # limite de segurança: não dormir mais que recv_window/2
            wait_ms = min(wait_ms, self.recv_window // 2)
            if wait_ms > 0:
                time.sleep(wait_ms / 1000.0)

    # ---------- Market data ----------
    def price(self, symbol):  # e.g., 'BTCUSDT'
        data = self.client.ticker_price(symbol)
        return float(data["price"])

    def account_balances(self):
        self._maybe_wait_if_ahead()
        acc = self.client.account(recvWindow=self.recv_window)
        return {b["asset"]: float(b["free"]) + float(b["locked"]) for b in acc["balances"]}

    # ---------- Trading ----------
    def order_market(self, symbol, side, quote_order_qty=None, quantity=None):
        self._maybe_wait_if_ahead()
        if quote_order_qty:
            return self.client.new_order(
                symbol=symbol, side=side, type="MARKET",
                quoteOrderQty=str(quote_order_qty), recvWindow=self.recv_window
            )
        else:
            return self.client.new_order(
                symbol=symbol, side=side, type="MARKET",
                quantity=str(quantity), recvWindow=self.recv_window
            )

    def order_limit(self, symbol, side, quantity, price, tif="GTC"):
        self._maybe_wait_if_ahead()
        return self.client.new_order(
            symbol=symbol, side=side, type="LIMIT", timeInForce=tif,
            quantity=str(quantity), price=str(price), recvWindow=self.recv_window
        )

    def exchange_info(self, symbol):
        # pública (não precisa aguardar)
        return self.client.exchange_info(symbol=symbol)
