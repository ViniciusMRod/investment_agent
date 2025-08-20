import math
import os
import csv
import time
from .logger import get_logger
from .env import Env
from .exchange import Exchange
from .market import Market
from .storage import Storage


log = get_logger()

class PortfolioManager:
    def __init__(self, env: Env, exchange: Exchange):
        self.env = env
        self.ex = exchange
        self.storage = Storage(self.env.DB_PATH)
        self.market = Market(self.ex)


    # --- State ---
    def refresh_positions(self):
        self.balances = self.ex.account_balances()
        # preços atuais dos símbolos que usamos no config
        self.prices = {}
        total = 0.0
        base = self.env.BASE_ASSET
        free_base = float(self.balances.get(base, 0.0))
        for s, pair in self.env.PAIRS.items():
            p = self.ex.price(pair)
            self.prices[s] = p
            qty = float(self.balances.get(s, 0.0))
            total += qty * p
        self.portfolio_value = total + free_base
        self.free_base = free_base


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

    def _majors(self):
        return {"BTC", "ETH"}

    def _open_positions(self):
        return self.storage.get("open_positions", {})

    def _save_positions(self, pos):
        self.storage.set("open_positions", pos)

    def _has_open(self, symbol):
        pos = self._open_positions().get(symbol, [])
        return len(pos) >= self.env.SAT_MAX_OPEN_PER_SYMBOL

    def _record_trade(self, row: dict):
        # salva no CSV para auditoria
        path = self.env.TRADES_CSV
        header = ["ts","action","symbol","qty","price","quote","note"]
        write_header = not os.path.exists(path)
        with open(path, "a", newline="") as f:
            w = csv.DictWriter(f, fieldnames=header)
            if write_header: w.writeheader()
            w.writerow(row)

    def satellite_entry(self):
        if not self.env.SAT_ENABLED:
            return ""
        entries = []
        for s in self.env.SAT_SYMBOLS:
            pair = self.env.PAIRS[s]
            closes = self.market.closes(pair, self.env.SAT_TIMEFRAME, limit=max(220, self.env.SAT_SMA_LEN+5))
            sma = self.market.sma(closes, self.env.SAT_SMA_LEN)
            if sma is None:
                continue
            last = closes[-1]
            if last <= sma:
                continue
            if self._has_open(s):
                continue
            stop_pct = self.env.SAT_STOP_PCT_MAJORS if s in self._majors() else self.env.SAT_STOP_PCT_ALTS
            risk_amt = self.env.RISK_PER_TRADE * self.portfolio_value
            quote_to_buy = max(0.0, risk_amt / stop_pct)
            if quote_to_buy < 5.0:
                continue
            # executa compra a mercado por valor em BASE (quote)
            try:
                if self.env.LIVE and self.env.API_KEY:
                    self.ex.order_market(symbol=pair, side="BUY", quote_order_qty=quote_to_buy)
                qty = quote_to_buy / last
                pos = self._open_positions()
                trade = {
                    "entry_price": float(last),
                    "qty": float(qty),
                    "stop_price": float(last * (1 - stop_pct)),
                    "trail_active": False,
                    "trail_anchor": float(last),
                    "tp_partial": float(last * (1 + self.env.SAT_TP_PARTIAL)),
                    "ts": time.time(),
                }
                arr = pos.get(s, [])
                arr.append(trade)
                pos[s] = arr
                self._save_positions(pos)
                entries.append(f"{s} BUY ~{quote_to_buy:.2f} {self.env.BASE_ASSET}")
                self._record_trade({
                    "ts": time.time(), "action":"BUY", "symbol": s,
                    "qty": qty, "price": last, "quote": quote_to_buy, "note":"sat_entry"
                })
            except Exception as e:
                from .logger import get_logger
                get_logger().exception(f"Erro satellite_entry {s}: {e}")
        return "; ".join(entries) if entries else ""

    def satellite_exit(self):
        if not self.env.SAT_ENABLED:
            return ""
        actions = []
        pos = self._open_positions()
        changed = False
        for s, arr in list(pos.items()):
            if not arr: 
                continue
            price = self.prices.get(s)
            pair = self.env.PAIRS[s]
            new_arr = []
            for p in arr:
                qty = p["qty"]
                stop = p["stop_price"]
                tp_partial = p["tp_partial"]
                # ativa trailing após parcial (realiza 1/3)
                if (not p.get("trail_active", False)) and price is not None and price >= tp_partial:
                    sell_qty = qty/3
                    try:
                        sell_qty_rounded = self._round_qty(pair, sell_qty)
                        if self.env.LIVE and self.env.API_KEY:
                            self.ex.order_market(symbol=pair, side="SELL", quantity=sell_qty_rounded)
                        self._record_trade({
                            "ts": time.time(),"action":"SELL","symbol":s,
                            "qty": sell_qty_rounded, "price": price, "quote": sell_qty_rounded*price, "note":"partial_tp"
                        })
                        actions.append(f"{s} TP parcial 1/3")
                        p["qty"] = qty - sell_qty_rounded
                        p["trail_active"] = True
                        p["trail_anchor"] = price
                        p["stop_price"] = max(p["stop_price"], p["entry_price"])
                        changed = True
                    except Exception as e:
                        from .logger import get_logger
                        get_logger().exception(f"Erro TP parcial {s}: {e}")
                # trailing stop
                if p.get("trail_active", False) and price is not None:
                    drop = 1.0 - (price / p["trail_anchor"])
                    trail_pct = self.env.SAT_TRAIL_PCT
                    if price > p["trail_anchor"]:
                        p["trail_anchor"] = price
                        changed = True
                    elif drop >= trail_pct:
                        sell_qty = p["qty"]
                        try:
                            sell_qty_rounded = self._round_qty(pair, sell_qty)
                            if self.env.LIVE and self.env.API_KEY:
                                self.ex.order_market(symbol=pair, side="SELL", quantity=sell_qty_rounded)
                            self._record_trade({
                                "ts": time.time(),"action":"SELL","symbol":s,
                                "qty": sell_qty_rounded,"price":price,"quote":sell_qty_rounded*price,"note":"trail_stop"
                            })
                            actions.append(f"{s} TRAIL stop")
                            changed = True
                            continue  # não mantém
                        except Exception as e:
                            from .logger import get_logger
                            get_logger().exception(f"Erro TRAIL {s}: {e}")
                # stop loss “duro”
                if price is not None and price <= p["stop_price"]:
                    sell_qty = p["qty"]
                    try:
                        sell_qty_rounded = self._round_qty(pair, sell_qty)
                        if self.env.LIVE and self.env.API_KEY:
                            self.ex.order_market(symbol=pair, side="SELL", quantity=sell_qty_rounded)
                        self._record_trade({
                            "ts": time.time(),"action":"SELL","symbol":s,
                            "qty": sell_qty_rounded,"price":price,"quote":sell_qty_rounded*price,"note":"hard_stop"
                        })
                        actions.append(f"{s} STOP")
                        changed = True
                        continue
                    except Exception as e:
                        from .logger import get_logger
                        get_logger().exception(f"Erro STOP {s}: {e}")
                # mantém posição
                new_arr.append(p)
            pos[s] = new_arr
        if changed:
            self._save_positions(pos)
        return "; ".join(actions) if actions else ""

