"""DataUpdateCoordinator for Guest Dashboard Guard."""
from __future__ import annotations

from datetime import datetime, timedelta
import logging
from typing import Any

from homeassistant.components import persistent_notification
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.components.lovelace import (
    DOMAIN as LOVELACE_DOMAIN,
)
from homeassistant.util import dt as dt_util

from .const import (
    DOMAIN,
    CONF_ACTION_MODE,
    CONF_GUEST_DETECTION,
    CONF_GUEST_USERS,
    CONF_CHECK_INTERVAL,
    ACTION_REVOKE,
    GUEST_NON_ADMIN,
    GUEST_SPECIFIC_USERS,
    DEFAULT_CHECK_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)


class DashboardGuardCoordinator(DataUpdateCoordinator):
    """Class to manage fetching dashboard data and checking guest access."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize coordinator."""
        self.config_entry = entry
        self._tracked_dashboards: set[str] = set()
        self._violations_detected: list[dict[str, Any]] = []

        check_interval = entry.data.get(CONF_CHECK_INTERVAL, DEFAULT_CHECK_INTERVAL)

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=check_interval),
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from Home Assistant."""
        try:
            dashboards = await self._get_dashboards()
            guest_users = await self._get_guest_users()

            violations = []
            new_dashboards = []

            for dashboard in dashboards:
                dashboard_key = dashboard["url_path"] or "default"

                # Check if this is a new dashboard
                if dashboard_key not in self._tracked_dashboards:
                    new_dashboards.append(dashboard_key)
                    self._tracked_dashboards.add(dashboard_key)

                    # Check for guest access violations
                    violation = await self._check_dashboard_access(
                        dashboard, guest_users
                    )
                    if violation:
                        violations.append(violation)

            # Handle violations
            if violations:
                await self._handle_violations(violations)

            self._violations_detected = violations

            return {
                "dashboards_count": len(dashboards),
                "guest_users_count": len(guest_users),
                "violations": violations,
                "last_check": dt_util.now(),
            }

        except Exception as err:
            _LOGGER.exception("Error fetching dashboard data: %s", err)
            raise UpdateFailed(f"Error communicating with Home Assistant: {err}")

    async def _get_dashboards(self) -> list[dict[str, Any]]:
        """Get all dashboards from Home Assistant."""
        dashboards = []

        try:
            # Use the storage collection to get all registered dashboards
            from homeassistant.components.lovelace import dashboard

            # Get the dashboard storage collection
            if LOVELACE_DOMAIN in self.hass.data:
                lovelace_data = self.hass.data[LOVELACE_DOMAIN]

                # Try to iterate through the dashboards
                if hasattr(lovelace_data, "dashboards"):
                    # Newer HA versions with dashboards attribute
                    for url_path, dash_config in lovelace_data.dashboards.items():
                        dashboards.append({
                            "url_path": url_path if url_path != "lovelace" else None,
                            "title": getattr(dash_config, "config", {}).get("title", url_path) if hasattr(dash_config, "config") else url_path,
                            "mode": getattr(dash_config, "mode", "storage") if hasattr(dash_config, "mode") else "storage",
                        })
                elif isinstance(lovelace_data, dict):
                    # Dictionary-based storage
                    for url_path, dash_config in lovelace_data.items():
                        dashboards.append({
                            "url_path": url_path if url_path != "lovelace" else None,
                            "title": getattr(dash_config, "config", {}).get("title", url_path) if hasattr(dash_config, "config") else url_path,
                            "mode": getattr(dash_config, "mode", "storage") if hasattr(dash_config, "mode") else "storage",
                        })
                else:
                    _LOGGER.debug("Lovelace data type: %s", type(lovelace_data))

            # Also try to get dashboards from lovelace storage collection
            try:
                dashboard_storage = self.hass.data.get("lovelace_dashboards")
                if dashboard_storage:
                    for dash_id, dash_data in dashboard_storage.items():
                        # Avoid duplicates
                        if not any(d["url_path"] == dash_id for d in dashboards):
                            dashboards.append({
                                "url_path": dash_id if dash_id != "lovelace" else None,
                                "title": dash_data.get("title", dash_id) if isinstance(dash_data, dict) else dash_id,
                                "mode": dash_data.get("mode", "storage") if isinstance(dash_data, dict) else "storage",
                            })
            except Exception as e:
                _LOGGER.debug("Could not access lovelace_dashboards: %s", e)

        except Exception as e:
            _LOGGER.exception("Error getting dashboards: %s", e)

        # Always add at least the default dashboard if none found
        if not dashboards:
            _LOGGER.warning("No dashboards detected, adding default dashboard")
            dashboards.append({
                "url_path": None,
                "title": "Home",
                "mode": "storage",
            })

        _LOGGER.info("Detected %d dashboard(s): %s", len(dashboards), [d["title"] for d in dashboards])
        return dashboards

    async def _get_guest_users(self) -> set[str]:
        """Get list of guest user IDs based on configuration."""
        guest_detection = self.config_entry.data.get(
            CONF_GUEST_DETECTION, GUEST_NON_ADMIN
        )

        guest_users = set()

        if guest_detection == GUEST_NON_ADMIN:
            # Consider all non-admin users as guests
            for user in await self.hass.auth.async_get_users():
                if not user.system_generated and not user.is_admin:
                    guest_users.add(user.id)

        elif guest_detection == GUEST_SPECIFIC_USERS:
            # Use specific user list from config
            guest_users = set(
                self.config_entry.data.get(CONF_GUEST_USERS, [])
            )

        return guest_users

    async def _check_dashboard_access(
        self, dashboard: dict[str, Any], guest_users: set[str]
    ) -> dict[str, Any] | None:
        """Check if a dashboard has guest access enabled."""
        # In Home Assistant, if a dashboard doesn't have explicit visibility restrictions,
        # all users can see it by default. This is the violation we're checking for.

        dashboard_key = dashboard["url_path"] or "default"

        # Try to get dashboard visibility settings
        visibility = await self._get_dashboard_visibility(dashboard)

        # If visibility is not restricted (None or empty), it's visible to all users
        if not visibility or visibility.get("visible_to_all", True):
            return {
                "dashboard": dashboard_key,
                "title": dashboard.get("title", dashboard_key),
                "issue": "Dashboard is visible to all users by default",
                "guest_users_affected": list(guest_users),
            }

        # Check if any guest users are in the visible_users list
        visible_users = visibility.get("visible_users", [])
        affected_guests = guest_users.intersection(set(visible_users))

        if affected_guests:
            return {
                "dashboard": dashboard_key,
                "title": dashboard.get("title", dashboard_key),
                "issue": f"Guest users have explicit access: {len(affected_guests)} user(s)",
                "guest_users_affected": list(affected_guests),
            }

        return None

    async def _get_dashboard_visibility(
        self, dashboard: dict[str, Any]
    ) -> dict[str, Any] | None:
        """Get visibility settings for a dashboard."""
        # This is a simplified implementation - actual implementation would need
        # to access Home Assistant's internal dashboard configuration
        # For now, we assume new dashboards are visible to all by default

        url_path = dashboard["url_path"]

        # Try to get the dashboard config
        try:
            lovelace = self.hass.data.get(LOVELACE_DOMAIN, {})
            # Use attribute access instead of dict .get() to avoid deprecation warning
            config_key = url_path or "lovelace"
            config = getattr(lovelace, config_key, None) if hasattr(lovelace, config_key) else lovelace.get(config_key) if isinstance(lovelace, dict) else None

            if config and hasattr(config, "config"):
                views_config = config.config
                # Check if there are visibility restrictions
                # This is a placeholder - actual implementation depends on HA version
                return views_config.get("visibility", {})

        except Exception as e:
            _LOGGER.debug("Could not get dashboard visibility: %s", e)

        return None

    async def _handle_violations(self, violations: list[dict[str, Any]]) -> None:
        """Handle detected violations based on action mode."""
        action_mode = self.config_entry.data.get(CONF_ACTION_MODE)

        for violation in violations:
            dashboard = violation["dashboard"]
            title = violation["title"]
            issue = violation["issue"]

            # Always notify
            message = (
                f"Dashboard '{title}' ({dashboard}) has a guest access issue:\n\n"
                f"{issue}\n\n"
                f"Guest users affected: {len(violation['guest_users_affected'])}"
            )

            if action_mode == ACTION_REVOKE:
                # TODO: Implement auto-revoke functionality
                # This requires modifying dashboard visibility settings
                message += "\n\nAttempting to revoke guest access..."

                revoke_success = await self._revoke_guest_access(dashboard)

                if revoke_success:
                    message += "\n✓ Guest access has been revoked successfully."
                else:
                    message += (
                        "\n✗ Failed to automatically revoke access. "
                        "Please review dashboard permissions manually."
                    )
            else:
                message += (
                    "\n\nPlease review the dashboard permissions in "
                    "Settings → Dashboards."
                )

            persistent_notification.async_create(
                self.hass,
                message,
                title="Guest Dashboard Guard Alert",
                notification_id=f"{DOMAIN}_{dashboard}",
            )

            _LOGGER.warning("Dashboard guest access violation detected: %s", violation)

    async def _revoke_guest_access(self, dashboard: str) -> bool:
        """Revoke guest access from a dashboard."""
        # This is a placeholder for the actual implementation
        # The actual implementation would need to:
        # 1. Get current dashboard configuration
        # 2. Modify visibility settings to exclude guest users
        # 3. Save the updated configuration

        # For now, we log that this would happen
        _LOGGER.info(
            "Would revoke guest access from dashboard: %s (not implemented yet)",
            dashboard,
        )

        # Return False to indicate manual intervention is needed
        return False
