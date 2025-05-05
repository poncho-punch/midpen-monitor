import os
from app.alerts.email_alert import send_email_alert

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # If python-dotenv is not installed, continue without error

def test_send_email():
    # Use environment variables or .env for SMTP settings
    print("SMTP_SERVER:", os.environ.get("ALERT_SMTP_SERVER"))
    print("SMTP_PORT:", os.environ.get("ALERT_SMTP_PORT"))
    print("SMTP_USER:", os.environ.get("ALERT_SMTP_USER"))
    print("SMTP_PASSWORD:", os.environ.get("ALERT_SMTP_PASSWORD"))
    print("FROM_EMAIL:", os.environ.get("ALERT_FROM_EMAIL"))
    to_email = os.environ.get("ALERT_TEST_RECIPIENT", "brianmharley@me.com")
    print("TO_EMAIL:", to_email)
    subject = "Test: Midpen Monitor Alert Email"
    body = "This is a test alert from the Midpen Monitor system."
    send_email_alert(to_email, subject, body)
    print(f"Test email sent to {to_email}")

if __name__ == "__main__":
    test_send_email()
