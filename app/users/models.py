class User:
    """Represents a subscriber/user."""
    def __init__(self, email=None, phone=None, zones=None):
        self.email = email
        self.phone = phone
        self.zones = zones or []  # List of preserve IDs

class Subscription:
    """Represents a user's alert subscription preferences."""
    def __init__(self, user_id, zones, alert_types):
        self.user_id = user_id
        self.zones = zones
        self.alert_types = alert_types
