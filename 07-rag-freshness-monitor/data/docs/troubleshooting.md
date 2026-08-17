# Login Failures
If login keeps failing, clear browser cookies and confirm two-factor authentication codes are entered within 30 seconds of being generated.

# Sync Errors
Sync errors are usually caused by an expired OAuth token. Reconnecting the integration from the settings page resolves most sync errors.

# Slow Dashboard Loading
Dashboards with more than 50 widgets may load slowly. Removing unused widgets or splitting the dashboard into multiple pages improves load time.

# Failed Webhook Deliveries
Failed webhook deliveries are retried three times with exponential backoff before being marked as permanently failed.
