import os
import smtplib
from email.mime.text import MIMEText

def send_alert_email(location, temp_c, receiver=None):
    sender = os.getenv("GMAIL_USER")
    password = os.getenv("GMAIL_APP_PASSWORD")
    receiver = receiver or os.getenv("ALERT_RECEIVER")

    if not sender or not password or not receiver:
        return False, "Email credentials missing"

    subject = f"🔥 Heat Alert: {location}"
    body = (
        f"Warning! Temperature in {location} is {temp_c:.1f}°C — "
        f"above the 30°C safe threshold.\n\n"
        f"Stay hydrated and avoid prolonged sun exposure."
    )

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = receiver

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender, password)
            server.sendmail(sender, receiver, msg.as_string())
        return True, "Email sent"
    except Exception as e:
        return False, str(e)