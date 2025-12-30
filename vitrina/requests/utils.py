from workalendar.europe import Lithuania


def is_working_day(date):
    cal = Lithuania()
    return cal.is_working_day(date)


def add_working_days(start_date, working_days):
    cal = Lithuania()
    return cal.add_working_days(start_date, working_days)
