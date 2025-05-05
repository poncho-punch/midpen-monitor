"""
Entry point for the Midpen Monitor micro SaaS service.
Handles audio monitoring, user management, alerting, and notifications.
"""

from app.audio.processor import AudioProcessor
from app.alerts.alert_manager import AlertManager
from app.users.models import User, Subscription
from app.notifications.notifier import Notifier

# Future: add API endpoints, DB setup, and orchestrate the workflow

def main():
    print("Midpen Monitor micro SaaS service starting...")
    from app.audio.processor import AudioProcessor
    import os
    from app.alerts.alert_manager import AlertManager
    audio_day = os.environ.get("AUDIO_DAY")
    processor = AudioProcessor()
    processor.run_monitoring_loop(start_day=audio_day)
    # --- AlertManager email test ---
    alert_manager = AlertManager()
    user_email = os.environ.get("ALERT_TEST_RECIPIENT", "brianmharley@me.com")
    alert_manager.send_email(user_email, "Test: Main App Email Alert", "This is a test alert sent from the main app workflow.")
    print(f"Test alert email sent to {user_email}")

if __name__ == "__main__":
    main()
