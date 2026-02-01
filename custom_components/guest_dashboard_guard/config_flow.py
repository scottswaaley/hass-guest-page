"""Config flow for Guest Dashboard Guard integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
import homeassistant.helpers.config_validation as cv

from .const import (
    DOMAIN,
    CONF_ACTION_MODE,
    CONF_GUEST_DETECTION,
    CONF_GUEST_USERS,
    CONF_CHECK_INTERVAL,
    ACTION_NOTIFY,
    ACTION_REVOKE,
    GUEST_NON_ADMIN,
    GUEST_SPECIFIC_USERS,
    DEFAULT_ACTION_MODE,
    DEFAULT_GUEST_DETECTION,
    DEFAULT_CHECK_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)


class GuestDashboardGuardConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Guest Dashboard Guard."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            await self.async_set_unique_id("guest_dashboard_guard")
            self._abort_if_unique_id_configured()

            return self.async_create_entry(
                title="Guest Dashboard Guard",
                data=user_input,
            )

        # Get list of users for the dropdown
        users = await self._get_users()
        user_options = {user["id"]: user["name"] for user in users}

        data_schema = vol.Schema(
            {
                vol.Required(CONF_ACTION_MODE, default=DEFAULT_ACTION_MODE): vol.In(
                    {
                        ACTION_NOTIFY: "Notify Only",
                        ACTION_REVOKE: "Auto-revoke and Notify",
                    }
                ),
                vol.Required(
                    CONF_GUEST_DETECTION, default=DEFAULT_GUEST_DETECTION
                ): vol.In(
                    {
                        GUEST_NON_ADMIN: "Non-admin Users",
                        GUEST_SPECIFIC_USERS: "Specific Users",
                    }
                ),
                vol.Optional(CONF_GUEST_USERS, default=[]): cv.multi_select(
                    user_options
                ),
                vol.Optional(
                    CONF_CHECK_INTERVAL, default=DEFAULT_CHECK_INTERVAL
                ): vol.All(vol.Coerce(int), vol.Range(min=10, max=3600)),
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> GuestDashboardGuardOptionsFlow:
        """Get the options flow for this handler."""
        return GuestDashboardGuardOptionsFlow(config_entry)

    async def _get_users(self) -> list[dict[str, str]]:
        """Get list of users from Home Assistant."""
        users = []
        try:
            await self.hass.async_add_executor_job(lambda: None)  # Ensure we have access
            user_collection = await self.hass.auth.async_get_users()
            for user in user_collection:
                if not user.system_generated:
                    users.append({"id": user.id, "name": user.name or user.id})
        except Exception as e:
            _LOGGER.error("Error getting users: %s", e)
        return users


class GuestDashboardGuardOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for Guest Dashboard Guard."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # Update the config entry data, not options
            self.hass.config_entries.async_update_entry(
                self.config_entry, data=user_input
            )
            return self.async_create_entry(title="", data={})

        # Get list of users for the dropdown
        try:
            users = await self._get_users()
            user_options = {user["id"]: user["name"] for user in users}
        except Exception as e:
            _LOGGER.exception("Failed to get users: %s", e)
            errors["base"] = "cannot_connect"
            user_options = {}

        current_data = self.config_entry.data

        options_schema = vol.Schema(
            {
                vol.Required(
                    CONF_ACTION_MODE,
                    default=current_data.get(CONF_ACTION_MODE, DEFAULT_ACTION_MODE),
                ): vol.In(
                    {
                        ACTION_NOTIFY: "Notify Only",
                        ACTION_REVOKE: "Auto-revoke and Notify",
                    }
                ),
                vol.Required(
                    CONF_GUEST_DETECTION,
                    default=current_data.get(
                        CONF_GUEST_DETECTION, DEFAULT_GUEST_DETECTION
                    ),
                ): vol.In(
                    {
                        GUEST_NON_ADMIN: "Non-admin Users",
                        GUEST_SPECIFIC_USERS: "Specific Users",
                    }
                ),
                vol.Optional(
                    CONF_GUEST_USERS,
                    default=current_data.get(CONF_GUEST_USERS, []),
                ): cv.multi_select(user_options) if user_options else vol.In([]),
                vol.Optional(
                    CONF_CHECK_INTERVAL,
                    default=current_data.get(CONF_CHECK_INTERVAL, DEFAULT_CHECK_INTERVAL),
                ): vol.All(vol.Coerce(int), vol.Range(min=10, max=3600)),
            }
        )

        return self.async_show_form(
            step_id="init",
            data_schema=options_schema,
            errors=errors,
        )

    async def _get_users(self) -> list[dict[str, str]]:
        """Get list of users from Home Assistant."""
        users = []
        try:
            await self.hass.async_add_executor_job(lambda: None)  # Ensure we have access
            user_collection = await self.hass.auth.async_get_users()
            for user in user_collection:
                if not user.system_generated:
                    users.append({"id": user.id, "name": user.name or user.id})
        except Exception as e:
            _LOGGER.error("Error getting users: %s", e)
        return users
