from binance.spot import Spot as Client
from .logger import get_logger

log = get_logger()

class Exchange:
    def __init__(self, env):
        self.env = env
        base_url = "https://testnet.binance.vision" if env.TESTNET else None
        self.client = Client(api_key=env.API_KEY, api_secret=env.API_SECRET, base_url=base_url)

    # --- Market data ---
    def price(self, symbol):  # e.g., 'BTCEUR'
        data = self.client.ticker_price(symbol)
        return float(data["price"])

    def account_balances(self):
        acc = self.client.account()
        balances = {b["asset"]: float(b["free"]) + float(b["locked"]) for b in acc["balances"]}
        return balances

    # --- Trading helpers ---
    def order_market(self, symbol, side, quote_order_qty=None, quantity=None):
        # Market order by quote (preferred for DCA)
        if quote_order_qty:
            return self.client.new_order(symbol=symbol, side=side, type="MARKET", quoteOrderQty=str(quote_order_qty))
        else:
            return self.client.new_order(symbol=symbol, side=side, type="MARKET", quantity=str(quantity))

    def order_limit(self, symbol, side, quantity, price, tif="GTC"):
        return self.client.new_order(symbol=symbol, side=side, type="LIMIT", timeInForce=tif, quantity=str(quantity), price=str(price))

    def exchange_info(self, symbol):
        info = self.client.exchange_info(symbol=symbol)
        return info
