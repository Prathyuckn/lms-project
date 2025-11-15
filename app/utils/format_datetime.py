from datetime import datetime, timedelta


def format_notification_datetime(timestamp):
    now = datetime.now()
    delta = now - timestamp

    if delta < timedelta(hours=24):
        hours_ago = int(delta.total_seconds() // 3600)
        return f"{hours_ago} hours ago" if hours_ago > 1 else "1 hour ago"
    else:
        return timestamp.strftime("%Y-%m-%d %H:%M:%S")
