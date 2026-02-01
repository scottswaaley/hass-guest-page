"""Constants for Guest Dashboard Guard integration."""

DOMAIN = "guest_dashboard_guard"

# Configuration options
CONF_ACTION_MODE = "action_mode"
CONF_GUEST_DETECTION = "guest_detection"
CONF_GUEST_USERS = "guest_users"
CONF_CHECK_INTERVAL = "check_interval"
CONF_IGNORED_DASHBOARDS = "ignored_dashboards"

# Action modes
ACTION_NOTIFY = "notify"
ACTION_REVOKE = "revoke"

# Guest detection modes
GUEST_NON_ADMIN = "non_admin"
GUEST_SPECIFIC_USERS = "specific_users"

# Defaults
DEFAULT_CHECK_INTERVAL = 60  # seconds
DEFAULT_ACTION_MODE = ACTION_NOTIFY
DEFAULT_GUEST_DETECTION = GUEST_NON_ADMIN
