# Guest Dashboard Guard for Home Assistant

A Home Assistant custom integration that monitors dashboard ownership to ensure guest users haven't accidentally received access to new dashboards by default.

## Features

- **Automatic Dashboard Monitoring**: Continuously checks all dashboards for guest access
- **Flexible Guest Detection**: Define guests as either non-admin users or specific user list
- **Configurable Actions**:
  - Notify only mode - sends persistent notifications when violations are detected
  - Auto-revoke mode - automatically removes guest access and notifies (requires manual configuration currently)
- **Real-time Sensors**: Provides sensors to track:
  - Number of monitored dashboards
  - Number of guest users
  - Access violations detected
- **Customizable Check Interval**: Set how frequently to scan dashboards (10-3600 seconds)

## Installation

### HACS Installation (Recommended)

1. Open HACS in your Home Assistant instance
2. Click on "Integrations"
3. Click the three dots in the top right corner
4. Select "Custom repositories"
5. Add this repository URL: `https://github.com/yourusername/hass-guest-dashboard-guard`
6. Select category: "Integration"
7. Click "Add"
8. Find "Guest Dashboard Guard" in HACS and click "Download"
9. Restart Home Assistant

### Manual Installation

1. Copy the `custom_components/guest_dashboard_guard` folder to your Home Assistant's `custom_components` directory
2. If the `custom_components` directory doesn't exist, create it in the same location as your `configuration.yaml`
3. Restart Home Assistant

## Configuration

### Initial Setup

1. Go to **Settings** → **Devices & Services**
2. Click **+ Add Integration**
3. Search for "Guest Dashboard Guard"
4. Configure the following options:

#### Action Mode
- **Notify Only**: Sends persistent notifications when new dashboards are detected with guest access
- **Auto-revoke and Notify**: Automatically removes guest access from new dashboards and sends notification (Note: Auto-revoke functionality requires additional configuration)

#### Guest Detection Method
- **Non-admin Users**: Considers all users without admin privileges as guests
- **Specific Users**: Manually select which users should be considered guests

#### Guest Users
If you selected "Specific Users" detection, select the users from the dropdown list

#### Check Interval
How often to check for dashboard access violations (10-3600 seconds, default: 60)

### Updating Configuration

You can update the configuration at any time:

1. Go to **Settings** → **Devices & Services**
2. Find "Guest Dashboard Guard"
3. Click **Configure**
4. Update your settings

## Usage

### Sensors

The integration provides three sensors:

1. **Monitored Dashboards** (`sensor.guest_dashboard_guard_monitored_dashboards`)
   - Shows the total number of dashboards being monitored

2. **Guest Users** (`sensor.guest_dashboard_guard_guest_users`)
   - Shows the number of users classified as guests

3. **Access Violations** (`sensor.guest_dashboard_guard_violations`)
   - Shows the number of dashboards with guest access violations
   - Attributes include detailed information about each violation

### Notifications

When a violation is detected, you'll receive a persistent notification with:
- Dashboard name and ID
- Description of the issue
- Number of guest users affected
- Action taken (if auto-revoke is enabled)

### Example Automation

You can create automations based on the sensors:

```yaml
automation:
  - alias: "Alert on Dashboard Access Violation"
    trigger:
      - platform: state
        entity_id: sensor.guest_dashboard_guard_violations
    condition:
      - condition: template
        value_template: "{{ states('sensor.guest_dashboard_guard_violations') | int > 0 }}"
    action:
      - service: notify.mobile_app
        data:
          title: "Dashboard Security Alert"
          message: >
            {{ states('sensor.guest_dashboard_guard_violations') }} dashboard(s)
            have guest access violations!
```

## How It Works

1. The integration polls Home Assistant at the configured interval
2. It retrieves all dashboards and checks their visibility settings
3. For each new dashboard detected:
   - Checks if the dashboard is visible to all users (default behavior)
   - Checks if any guest users have explicit access
4. If a violation is found:
   - Creates a persistent notification
   - Updates the violation sensor
   - Optionally revokes guest access (if configured)

## Limitations

- **Auto-revoke functionality**: Currently logs the intent but requires manual dashboard permission configuration. This is because Home Assistant's dashboard permission API varies by version.
- **Dashboard visibility detection**: The integration assumes new dashboards are visible to all users by default (Home Assistant's standard behavior)
- **Storage mode dashboards**: Works best with storage mode dashboards. YAML mode dashboards have limited visibility control.

## Troubleshooting

### No dashboards detected

Check the logs for errors. The integration tries multiple methods to fetch dashboard information. If you're using YAML mode dashboards, they may not be detected.

### False positives

If you're getting notifications for dashboards that shouldn't trigger alerts:
- Verify your guest user configuration
- Check if the dashboard has proper visibility restrictions set
- Review the violation sensor attributes for detailed information

### Integration not loading

1. Check Home Assistant logs for errors
2. Verify all files are in the correct location
3. Ensure you've restarted Home Assistant after installation
4. Check that your Home Assistant version is compatible (2023.1+)

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License.

## Support

If you encounter issues:
1. Check the [Issues](https://github.com/yourusername/hass-guest-dashboard-guard/issues) page
2. Enable debug logging by adding to your `configuration.yaml`:
   ```yaml
   logger:
     logs:
       custom_components.guest_dashboard_guard: debug
   ```
3. Create a new issue with relevant logs and details

## Credits

Created to help Home Assistant users maintain better control over dashboard access for guest users.
