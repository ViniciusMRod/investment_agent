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

log = get_logger()

def main():
    env = Env()
    tz = pytz.timezone(os.getenv("TZ", "America/Sao_Paulo"))
    ex = Exchange(env=env)
    pm = PortfolioManager(env=env, exchange=ex)
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

        time.sleep(env.TICK_SECONDS)

if __name__ == "__main__":
    main()
