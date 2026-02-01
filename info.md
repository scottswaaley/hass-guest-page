# Guest Dashboard Guard

Monitor dashboard ownership to ensure guest users haven't accidentally received access to new dashboards by default.

## Features

- **Automatic Dashboard Monitoring**: Continuously checks all dashboards for guest access
- **Flexible Guest Detection**: Define guests as either non-admin users or specific user list
- **Configurable Actions**:
  - Notify only mode - sends persistent notifications when violations are detected
  - Auto-revoke mode - automatically removes guest access and notifies
- **Real-time Sensors**: Track monitored dashboards, guest users, and access violations
- **Customizable Check Interval**: Set how frequently to scan dashboards (10-3600 seconds)

## Quick Start

1. Install via HACS
2. Go to Settings → Devices & Services → Add Integration
3. Search for "Guest Dashboard Guard"
4. Configure your preferences:
   - Action Mode (notify or auto-revoke)
   - Guest Detection Method (non-admin users or specific users)
   - Check interval

## Sensors

The integration provides three sensors:
- **Monitored Dashboards**: Total number of dashboards being monitored
- **Guest Users**: Number of users classified as guests
- **Access Violations**: Number of dashboards with guest access violations (includes detailed attributes)

## Support

For issues, questions, or feature requests, please visit the [GitHub repository](https://github.com/scottswaaley/hass-guest-page).
