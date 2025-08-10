import os
import time
import datetime as dt
import pytz

from .services.logger import get_logger
from .services.env import Env
from .services.exchange import Exchange
from .services.portfolio import PortfolioManager
from .services.scheduler import should_run_monthly, should_run_weekly
from .services.notifier import Notifier
from .services.market import Market
from .services.storage import Storage
from .services.risk import RiskManager


log = get_logger()

def main():
    env = Env()
    tz = pytz.timezone(os.getenv("TZ", "America/Sao_Paulo"))
    ex = Exchange(env=env)
    pm = PortfolioManager(env=env, exchange=ex)
    storage = Storage(env.DB_PATH)
    risk = RiskManager(env=env, storage=storage, tz=tz)
    notifier = Notifier(env=env)

    last_run = {"dca": None, "rebalance": None}

    log.info("Agent started. TESTNET=%s LIVE=%s", env.TESTNET, env.LIVE)
    notifier.safe_send("🚀 Agent iniciado. TESTNET=%s LIVE=%s" % (env.TESTNET, env.LIVE))

    while True:
        # Kill-switch
        if os.path.exists(env.KILL_SWITCH_FILE):
            log.warning("Kill switch ativo. Pausando loop...")
            time.sleep(30)
            continue

        now = dt.datetime.now(tz)

        # Atualiza posições e patrimônio
        try:
            pm.refresh_positions()
        except Exception as e:
            log.exception("Erro ao atualizar posições: %s", e)
            time.sleep(5)
            continue  # <-- volta ao próximo ciclo em vez de seguir


        # DCA mensal
        try:
            if env.DCA_ENABLED and should_run_monthly(now, env.DCA_DAY, last_run["dca"]):
                spent = pm.run_dca()
                last_run["dca"] = now
                notifier.safe_send(f"📥 DCA executado no valor de {spent:.2f} {env.DCA_BASE_ASSET}")
        except Exception as e:
            log.exception("Erro no DCA: %s", e)

        # Rebalance semanal
        try:
            if env.REBALANCE_ENABLED and should_run_weekly(now, env.REBALANCE_WEEKDAY, last_run["rebalance"]):
                summary = pm.run_rebalance()
                last_run["rebalance"] = now
                notifier.safe_send("⚖️ Rebalance semanal: " + summary)
        except Exception as e:
            log.exception("Erro no rebalance: %s", e)
        
        # Satélite (entradas e saídas)
        try:
            if env.SAT_ENABLED:
                can, reason = risk.can_trade(pm.portfolio_value)
                # saídas SEMPRE avaliadas (mesmo se não puder abrir novas)
                exit_actions = pm.satellite_exit()
                if exit_actions:
                    notifier.safe_send("🔻 Sat exits: " + exit_actions)

                if can:
                    entry_actions = pm.satellite_entry()
                    if entry_actions:
                        notifier.safe_send("🔼 Sat entries: " + entry_actions)
                        risk.count_order()
                else:
                    if reason == "daily_loss_cap":
                        log.warning("Circuit breaker: daily loss cap atingido.")
                    elif reason == "max_orders":
                        log.warning("Circuit breaker: limite diário de ordens.")
        except Exception as e:
            log.exception("Erro satélite: %s", e)


        time.sleep(env.TICK_SECONDS)

if __name__ == "__main__":
    main()
