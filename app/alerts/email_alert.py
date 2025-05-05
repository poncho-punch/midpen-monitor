import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os

import logging
import traceback

def send_email_alert(to_email: str, subject: str, body: str):
    smtp_server = os.environ.get("ALERT_SMTP_SERVER")
    smtp_port = int(os.environ.get("ALERT_SMTP_PORT", 587))
    smtp_user = os.environ.get("ALERT_SMTP_USER")
    smtp_password = os.environ.get("ALERT_SMTP_PASSWORD")
    from_email = os.environ.get("ALERT_FROM_EMAIL", smtp_user)

    logger = logging.getLogger("alerts.email_alert")
    logger.info(f"Preparing to send email: to={to_email}, subject={subject}, smtp_server={smtp_server}, smtp_port={smtp_port}, smtp_user={smtp_user}, from_email={from_email}")
    logger.debug(f"Email body: {body}")

    if not all([smtp_server, smtp_user, smtp_password, to_email]):
        logger.error("Missing SMTP configuration or recipient email.")
        return False

    msg = MIMEMultipart()
    msg["From"] = from_email
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            logger.info(f"SMTP login successful. Sending email to {to_email}...")
            server.sendmail(from_email, to_email, msg.as_string())
            logger.info(f"Email sent to {to_email}.")
        return True
    except Exception as e:
        logger.error(f"Exception occurred while sending email to {to_email}: {e}")
        logger.error(traceback.format_exc())
        return False

