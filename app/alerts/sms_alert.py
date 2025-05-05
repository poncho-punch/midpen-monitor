import os
from typing import Optional
from twilio.rest import Client

def send_sms_alert(to_number: str, body: str, from_number: Optional[str] = None):
    account_sid = os.environ.get("TWILIO_ACCOUNT_SID")
    auth_token = os.environ.get("TWILIO_AUTH_TOKEN")
    from_number = from_number or os.environ.get("TWILIO_FROM_NUMBER")

    if not all([account_sid, auth_token, from_number, to_number]):
        raise ValueError("Missing Twilio configuration or phone number.")

    client = Client(account_sid, auth_token)
    message = client.messages.create(
        body=body,
        from_=from_number,
        to=to_number
    )
    return message.sid
