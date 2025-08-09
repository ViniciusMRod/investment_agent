import math
import os
import csv
import time
from .logger import get_logger
from .env import Env
from .exchange import Exchange

log = get_logger()

class PortfolioManager:
    def __init__(self, env: Env, exchange: Exchange):
        self.env = env
        self.ex = exchange

    # --- State ---
    def refresh_positions(self):
        self.balances = self.ex.account_balances()
        self.prices = {sym: self.ex.price(self.env.PAIRS[sym]) for sym in self.env.PAIRS.keys()}
        self.base_balance = self.balances.get(self.env.BASE_ASSET, 0.0)
        self.portfolio_value = self.base_balance
        for sym, pair in self.env.PAIRS.items():
            qty = self.balances.get(sym, 0.0)
            self.portfolio_value += qty * self.prices[sym]
        log.info(f"Patrimônio: {self.portfolio_value:.2f} {self.env.BASE_ASSET} | Base livre: {self.base_balance:.2f}")

    def current_weights(self):
        weights = {}
        if self.portfolio_value <= 0: return {k:0 for k in self.env.PAIRS.keys()}
        for sym in self.env.PAIRS.keys():
            qty = self.balances.get(sym, 0.0)
            val = qty * self.prices[sym]
            weights[sym] = val / self.portfolio_value
        return weights

    # --- DCA ---
    def run_dca(self):
        amount = self.env.DCA_AMOUNT_BASE
        base_asset = self.env.DCA_BASE_ASSET or self.env.BASE_ASSET
        symbols = self.env.DCA_SYMBOLS

        # Distribui conforme targets, mas se algum ativo estiver abaixo >2 p.p., prioriza
        weights = self.current_weights()
        deltas = {s: self.env.TARGETS[s] - weights.get(s, 0.0) for s in symbols}
        priority = sorted(symbols, key=lambda s: deltas[s], reverse=True)

        spent = 0.0
        for s in priority:
            target_part = self.env.TARGETS[s]
            alloc = amount * target_part
            if alloc <= 0: continue
            pair = self.env.PAIRS[s]
            price = self.prices[s]
            # comprar por valor (quote)
            try:
                if self.env.LIVE and self.env.API_KEY:
                    self.ex.order_market(symbol=pair, side="BUY", quote_order_qty=alloc)
                spent += alloc
                log.info(f"DCA BUY {s} {alloc:.2f} {base_asset} (~{alloc/price:.6f} {s})")
            except Exception as e:
                log.exception(f"Erro DCA {s}: {e}")
        return spent

    # --- Rebalance ---
    def run_rebalance(self):
        weights = self.current_weights()
        tol = self.env.REBALANCE_TOLERANCE
        actions = []
        # Vende quem está acima e compra quem está abaixo, usando base asset intermediário
        to_sell = [s for s in weights if weights[s] > self.env.TARGETS[s] + tol]
        to_buy = [s for s in weights if weights[s] < self.env.TARGETS[s] - tol]

        # vende excedentes
        for s in to_sell:
            w = weights[s]
            target = self.env.TARGETS[s]
            excess_val = (w - target) * self.portfolio_value
            if excess_val <= 0: continue
            qty = excess_val / self.prices[s]
            pair = self.env.PAIRS[s]
            try:
                if self.env.LIVE and self.env.API_KEY:
                    # vender a mercado
                    self.ex.order_market(symbol=pair, side="SELL", quantity=round_qty(self.ex, pair, qty))
                actions.append(f"SELL {s} {qty:.6f}")
                log.info(f"Rebalance SELL {s} qty={qty:.6f}")
            except Exception as e:
                log.exception(f"Erro SELL {s}: {e}")

        # recomputa base livre
        self.refresh_positions()

        # compra faltantes
        for s in to_buy:
            w = self.current_weights()[s]
            target = self.env.TARGETS[s]
            deficit_val = (target - w) * self.portfolio_value
            if deficit_val <= 0: continue
            pair = self.env.PAIRS[s]
            try:
                if self.env.LIVE and self.env.API_KEY:
                    self.ex.order_market(symbol=pair, side="BUY", quote_order_qty=deficit_val)
                actions.append(f"BUY {s} {deficit_val:.2f} {self.env.BASE_ASSET}")
                log.info(f"Rebalance BUY {s} quote={deficit_val:.2f}")
            except Exception as e:
                log.exception(f"Erro BUY {s}: {e}")

        return "; ".join(actions) if actions else "Sem ações (dentro da banda)."

def round_qty(exchange, symbol, qty):
    # Ajusta quantidade pela lot size mínima
    info = exchange.exchange_info(symbol)
    for f in info["symbols"][0]["filters"]:
        if f["filterType"] == "LOT_SIZE":
            step = float(f["stepSize"])
            if step > 0:
                return math.floor(qty/step)*step
    return qty
