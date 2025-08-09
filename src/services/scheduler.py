import datetime as dt

def should_run_monthly(now, day, last_run):
    if last_run is None:
        # roda no primeiro ciclo se já passou do dia
        return now.day >= day
    return (now.date().month != last_run.date().month) and (now.day >= day)

def should_run_weekly(now, weekday, last_run):
    if last_run is None:
        return now.weekday() == weekday
    return (now.date() - last_run.date()).days >= 7 and now.weekday() == weekday
