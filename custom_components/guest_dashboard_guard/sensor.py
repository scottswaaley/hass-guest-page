"""Sensor platform for Guest Dashboard Guard."""
from __future__ import annotations

from homeassistant.components.sensor import (
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import DashboardGuardCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensor platform."""
    coordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities(
        [
            DashboardCountSensor(coordinator),
            GuestUsersCountSensor(coordinator),
            ViolationsSensor(coordinator),
        ]
    )


class DashboardGuardSensorBase(CoordinatorEntity, SensorEntity):
    """Base class for Guest Dashboard Guard sensors."""

    def __init__(self, coordinator: DashboardGuardCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_has_entity_name = True

    @property
    def device_info(self):
        """Return device information about this entity."""
        return {
            "identifiers": {(DOMAIN, "guest_dashboard_guard")},
            "name": "Guest Dashboard Guard",
            "manufacturer": "Custom",
            "model": "Dashboard Monitor",
        }


class DashboardCountSensor(DashboardGuardSensorBase):
    """Sensor showing the number of monitored dashboards."""

    def __init__(self, coordinator: DashboardGuardCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{DOMAIN}_dashboards_count"
        self._attr_name = "Monitored Dashboards"
        self._attr_icon = "mdi:view-dashboard"
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self) -> int | None:
        """Return the state of the sensor."""
        if self.coordinator.data:
            return self.coordinator.data.get("dashboards_count", 0)
        return None


class GuestUsersCountSensor(DashboardGuardSensorBase):
    """Sensor showing the number of guest users."""

    def __init__(self, coordinator: DashboardGuardCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{DOMAIN}_guest_users_count"
        self._attr_name = "Guest Users"
        self._attr_icon = "mdi:account-group"
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self) -> int | None:
        """Return the state of the sensor."""
        if self.coordinator.data:
            return self.coordinator.data.get("guest_users_count", 0)
        return None


class ViolationsSensor(DashboardGuardSensorBase):
    """Sensor showing detected violations."""

    def __init__(self, coordinator: DashboardGuardCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{DOMAIN}_violations"
        self._attr_name = "Access Violations"
        self._attr_icon = "mdi:alert-circle"
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self) -> int:
        """Return the state of the sensor."""
        if self.coordinator.data:
            violations = self.coordinator.data.get("violations", [])
            return len(violations)
        return 0

    @property
    def extra_state_attributes(self) -> dict:
        """Return additional attributes."""
        if self.coordinator.data:
            violations = self.coordinator.data.get("violations", [])
            last_check = self.coordinator.data.get("last_check")

            return {
                "violations": violations,
                "last_check": last_check,
            }
        return {}
