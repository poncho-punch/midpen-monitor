from .email_alert import send_email_alert
from .sms_alert import send_sms_alert
from .zones import ZONES

class AlertManager:
    """Handles keyword detection and alert triggering."""
    def __init__(self):
        pass

    def send_email(self, to_email, subject, body):
        import logging
        logger = logging.getLogger("alerts.alert_manager")
        logger.info(f"[AlertManager] About to send email to {to_email} with subject '{subject}' and body: {body}")
        try:
            result = send_email_alert(to_email, subject, body)
            if result:
                logger.info(f"[AlertManager] Email alert sent to {to_email}.")
            else:
                logger.warning(f"[AlertManager] Email alert to {to_email} may have failed. Check logs for details.")
        except Exception as e:
            logger.error(f"[AlertManager] Exception while sending email to {to_email}: {e}")
            import traceback
            logger.error(traceback.format_exc())

    def send_sms(self, to_number, body):
        send_sms_alert(to_number, body)

    def check_and_trigger(self, transcript, user_prefs, alert_type="email", event_unixtime=None):
        # Treat zones as keywords if keywords is empty
        keywords = user_prefs.get("keywords", [])
        zones = user_prefs.get("zones", [])
        # Always use the union of keywords and zones for matching
        all_keywords = list(set(keywords + zones))
        email = user_prefs.get("email")
        phone = user_prefs.get("phone")
        found = False
        matched_keyword = None
        for kw in all_keywords:
            kw_clean = kw.strip().lower()
            transcript_clean = transcript.lower()
            import logging
            logger = logging.getLogger("alerts.alert_manager")
            logger.debug(f"[Alert Debug] Checking keyword/zone: '{kw}' (clean: '{kw_clean}') in transcript: '{transcript[:80]}'")
            if kw_clean in transcript_clean:
                logger.info(f"[Alert Debug] MATCH FOUND: '{kw_clean}' in transcript.")
                found = True
                matched_keyword = kw
                break
        if not found:
            print("[AlertManager] No alert triggered: no keywords/zones found in transcript.")
            return
        import os
        from datetime import datetime, timezone
        alert_env = os.environ.get("ALERT_ENV", "DEV")
        # Use the event_unixtime if provided, else fallback to now
        if event_unixtime is not None:
            event_dt_utc = datetime.fromtimestamp(event_unixtime, tz=timezone.utc)
        else:
            event_dt_utc = datetime.utcnow().replace(microsecond=0, tzinfo=timezone.utc)
        # Freshness check: only alert if event is less than 1 hour old
        now_utc = datetime.now(timezone.utc)
        event_age_seconds = (now_utc - event_dt_utc).total_seconds()
        if event_age_seconds > 3600:
            import logging
            logger = logging.getLogger("alerts.alert_manager")
            logger.info(f"[AlertManager] Skipping alert for old segment: event age {event_age_seconds/60:.1f} min > 60 min")
            return
        user_timezone = user_prefs.get("timezone")
        local_time_str = None
        if user_timezone:
            try:
                from zoneinfo import ZoneInfo
                local_time = event_dt_utc.astimezone(ZoneInfo(user_timezone))
                local_time_str = local_time.strftime("%Y-%m-%d %H:%M:%S %Z")
            except Exception as e:
                local_time_str = None  # Fallback if error
        subject = f"Midpen Monitor Alert [{alert_env}]"
        body = f"Environment: {alert_env}\n"
        if local_time_str:
            body += f"Event Time: {local_time_str}\n"
        else:
            body += f"Event Time (UTC): {event_dt_utc.strftime('%Y-%m-%d %H:%M:%S UTC')}\n"
        body += f"Keyword/Zone: '{matched_keyword}' detected in transcript:\n{transcript}"

        if alert_type == "email" and email:
            import logging
            logger = logging.getLogger("alerts.alert_manager")
            logger.info(f"[AlertManager] Sending email alert to {email}...")
            self.send_email(email, subject, body)
            logger.info(f"[AlertManager] Finished processing email alert to {email}.")
        elif alert_type == "sms" and phone:
            print(f"[AlertManager] Sending SMS alert to {phone}...")
            self.send_sms(phone, body)
            print(f"[AlertManager] SMS alert sent to {phone}.")
