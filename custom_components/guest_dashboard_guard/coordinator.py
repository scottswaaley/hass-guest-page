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
from homeassistant.components.lovelace.const import LOVELACE_DATA
from homeassistant.components.frontend import DATA_PANELS
from homeassistant.util import dt as dt_util

from .const import (
    DOMAIN,
    CONF_ACTION_MODE,
    CONF_GUEST_DETECTION,
    CONF_GUEST_USERS,
    CONF_CHECK_INTERVAL,
    CONF_IGNORED_DASHBOARDS,
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
        """Get all dashboards from Home Assistant (Lovelace + Frontend Panels)."""
        dashboards = []

        # Part 1: Get Lovelace dashboards (storage/YAML mode)
        try:
            # Try the correct LOVELACE_DATA constant first
            if LOVELACE_DATA in self.hass.data:
                lovelace_data = self.hass.data[LOVELACE_DATA]
                _LOGGER.debug("Found LOVELACE_DATA, type: %s", type(lovelace_data))

                if hasattr(lovelace_data, "dashboards"):
                    for url_path, dash_config in lovelace_data.dashboards.items():
                        config_data = getattr(dash_config, "config", None)
                        title = config_data.get("title", url_path) if config_data and isinstance(config_data, dict) else url_path
                        require_admin = getattr(dash_config, "require_admin", False)
                        dashboards.append({
                            "url_path": url_path if url_path != "lovelace" else None,
                            "title": title,
                            "mode": getattr(dash_config, "mode", "storage") if hasattr(dash_config, "mode") else "storage",
                            "type": "lovelace",
                            "require_admin": require_admin,
                        })
            # Fallback to old LOVELACE_DOMAIN method for compatibility
            elif LOVELACE_DOMAIN in self.hass.data:
                lovelace_data = self.hass.data[LOVELACE_DOMAIN]
                _LOGGER.debug("Found LOVELACE_DOMAIN (fallback), type: %s", type(lovelace_data))

                if hasattr(lovelace_data, "dashboards"):
                    for url_path, dash_config in lovelace_data.dashboards.items():
                        config_data = getattr(dash_config, "config", None)
                        title = config_data.get("title", url_path) if config_data and isinstance(config_data, dict) else url_path
                        require_admin = getattr(dash_config, "require_admin", False)
                        dashboards.append({
                            "url_path": url_path if url_path != "lovelace" else None,
                            "title": title,
                            "mode": getattr(dash_config, "mode", "storage") if hasattr(dash_config, "mode") else "storage",
                            "type": "lovelace",
                            "require_admin": require_admin,
                        })
                elif isinstance(lovelace_data, dict):
                    for url_path, dash_config in lovelace_data.items():
                        config_data = getattr(dash_config, "config", None) if dash_config else None
                        title = config_data.get("title", url_path) if config_data and isinstance(config_data, dict) else url_path
                        require_admin = getattr(dash_config, "require_admin", False) if dash_config else False
                        dashboards.append({
                            "url_path": url_path if url_path != "lovelace" else None,
                            "title": title,
                            "mode": getattr(dash_config, "mode", "storage") if dash_config and hasattr(dash_config, "mode") else "storage",
                            "type": "lovelace",
                            "require_admin": require_admin,
                        })
        except Exception as e:
            _LOGGER.exception("Error getting Lovelace dashboards: %s", e)

        # Part 2: Get Frontend Panel dashboards (All panels, user can filter via config)
        try:
            if DATA_PANELS in self.hass.data:
                panels = self.hass.data[DATA_PANELS]
                _LOGGER.debug("Found DATA_PANELS with %d panels", len(panels))

                for panel_key, panel in panels.items():
                    panel_info = panel.to_response()
                    component_name = panel_info.get("component_name", "")

                    # Avoid duplicates with Lovelace dashboards
                    if not any(d.get("url_path") == panel_key for d in dashboards):
                        dashboards.append({
                            "url_path": panel_key,
                            "title": panel_info.get("title", panel_key),
                            "mode": "panel",
                            "type": "frontend_panel",
                            "component_name": component_name,
                            "require_admin": panel_info.get("require_admin", False),
                        })
                        _LOGGER.debug("Added frontend panel: %s (%s, component: %s)", panel_key, panel_info.get("title"), component_name)
        except Exception as e:
            _LOGGER.exception("Error getting frontend panels: %s", e)

        # Remove duplicates based on url_path (keep first occurrence)
        seen_paths = set()
        unique_dashboards = []
        for dashboard in dashboards:
            path_key = dashboard["url_path"]
            if path_key not in seen_paths:
                seen_paths.add(path_key)
                unique_dashboards.append(dashboard)
            else:
                _LOGGER.debug("Skipping duplicate dashboard: %s (%s)", path_key, dashboard.get("title"))

        dashboards = unique_dashboards

        # Filter out ignored dashboards based on user configuration
        ignored_dashboards = set(self.config_entry.data.get(CONF_IGNORED_DASHBOARDS, []))
        if ignored_dashboards:
            _LOGGER.debug("Ignoring configured dashboards: %s", ignored_dashboards)
            filtered_dashboards = []
            for dashboard in dashboards:
                # Check both url_path and "default" key for None url_path
                path_key = dashboard["url_path"] if dashboard["url_path"] is not None else "default"
                if path_key not in ignored_dashboards:
                    filtered_dashboards.append(dashboard)
                else:
                    _LOGGER.debug("Ignoring dashboard: %s (%s)", path_key, dashboard.get("title"))
            dashboards = filtered_dashboards

        # Always add at least the default dashboard if none found
        if not dashboards:
            _LOGGER.warning("No dashboards detected, adding default dashboard")
            dashboards.append({
                "url_path": None,
                "title": "Home",
                "mode": "storage",
                "type": "lovelace",
                "require_admin": False,
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

        # Dashboards/panels with require_admin are already protected
        if dashboard.get("require_admin", False):
            _LOGGER.debug("Dashboard %s (%s) requires admin, skipping check", dashboard_key, dashboard.get("title"))
            return None

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
