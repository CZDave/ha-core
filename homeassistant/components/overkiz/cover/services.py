"""Services definition."""

from pyoverkiz.enums import OverkizCommand
from pyoverkiz.exceptions import BaseOverkizException
from pyoverkiz.models import Action, Command
import voluptuous as vol

from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError

from ..const import DOMAIN
from ..coordinator import OverkizDataUpdateCoordinator
from .generic_cover import (
    COMMANDS_CLOSE,
    COMMANDS_OPEN,
    COMMANDS_SET_TILT_POSITION,
    COMMANDS_STOP,
    OverkizGenericCover,
)

BATCH_SET_COVER_TILT_POSITION_SERVICE_SCHEMA = vol.Schema(
    {
        vol.Required("tilt"): int,
        vol.Required("entities"): list,
    }
)

BATCH_SET_COVER_POSITION_SERVICE_SCHEMA = vol.Schema(
    {
        vol.Required("position"): int,
        vol.Required("entities"): list,
    }
)

BATCH_OPEN_COVER_SERVICE_SCHEMA = vol.Schema(
    {
        vol.Required("entities"): list,
    }
)

BATCH_CLOSE_COVER_SERVICE_SCHEMA = vol.Schema(
    {
        vol.Required("entities"): list,
    }
)

BATCH_STOP_COVER_SERVICE_SCHEMA = vol.Schema(
    {
        vol.Required("entities"): list,
    }
)


class ServicesSetup:
    """Registers integration services."""

    def __init__(
        self,
        hass: HomeAssistant,
        coordinator: OverkizDataUpdateCoordinator,
        coverEntities: list[OverkizGenericCover],
    ) -> None:
        """Initialize services."""

        self.hass = hass
        self.coordinator = coordinator
        self.entities: dict[str, OverkizGenericCover] = {
            e.entity_id: e for e in coverEntities
        }

        hass.services.async_register(
            DOMAIN,
            "batch_set_cover_tilt_position",
            self.batch_set_cover_tilt_position,
            schema=BATCH_SET_COVER_TILT_POSITION_SERVICE_SCHEMA,
        )
        hass.services.async_register(
            DOMAIN,
            "batch_set_cover_position",
            self.batch_set_cover_position,
            schema=BATCH_SET_COVER_POSITION_SERVICE_SCHEMA,
        )
        hass.services.async_register(
            DOMAIN,
            "batch_open_cover",
            self.batch_open_cover,
            schema=BATCH_OPEN_COVER_SERVICE_SCHEMA,
        )
        hass.services.async_register(
            DOMAIN,
            "batch_close_cover",
            self.batch_close_cover,
            schema=BATCH_CLOSE_COVER_SERVICE_SCHEMA,
        )
        hass.services.async_register(
            DOMAIN,
            "batch_stop_cover",
            self.batch_stop_cover,
            schema=BATCH_STOP_COVER_SERVICE_SCHEMA,
        )

    def __extract_group_entities(self, group_id: str) -> list[str]:
        """Extract individual entity IDs from a group entity ID."""

        # Get entity state
        state = self.hass.states.get(group_id)
        if not state:
            return []

        # Groups contain "entity_id" attribute
        if "entity_id" not in state.attributes:
            # Not a group, check if entity is registered in overkiz
            if group_id in self.entities:
                return [group_id]
            return []

        # Return all entities from the group if they're registered in overkiz
        return [
            entity_id
            for entity_id in state.attributes.get("entity_id", [])
            if entity_id in self.entities
        ]

    def __get_entities_from_call(
        self, service_call: ServiceCall
    ) -> list[OverkizGenericCover]:
        """Get all the individual cover entities from service call."""

        entities: list[OverkizGenericCover] = []
        for entity_id_arg in service_call.data["entities"]:
            entities.extend(
                [
                    self.entities[entity_id]
                    for entity_id in self.__extract_group_entities(entity_id_arg)
                ]
            )
        return entities

    async def __execute_actions(self, actions: list[Action]) -> None:
        try:
            await self.coordinator.client.execute_actions(
                actions,
                "Home Assistant",
            )
        # Catch Overkiz exceptions to support `continue_on_error` functionality
        except BaseOverkizException as exception:
            raise HomeAssistantError(exception) from exception

    async def batch_set_cover_tilt_position(self, service_call: ServiceCall) -> None:
        """Batch set tilt for selected covers."""

        tilt = 100 - service_call.data["tilt"]
        entities = self.__get_entities_from_call(service_call)

        actions = [
            Action(entity.device_url, [Command(command, [tilt])])
            for entity in entities
            if (command := entity.executor.select_command(*COMMANDS_SET_TILT_POSITION))
        ]

        await self.__execute_actions(actions)

    async def batch_set_cover_position(self, service_call: ServiceCall) -> None:
        """Batch set position for selected covers."""

        position = 100 - service_call.data["position"]
        entities = self.__get_entities_from_call(service_call)

        actions = [
            Action(entity.device_url, [Command(command, [position])])
            for entity in entities
            if (command := entity.executor.select_command(OverkizCommand.SET_CLOSURE))
        ]

        await self.__execute_actions(actions)

    async def batch_open_cover(self, service_call: ServiceCall) -> None:
        """Batch open selected covers."""

        entities = self.__get_entities_from_call(service_call)

        actions = [
            Action(entity.device_url, [Command(command)])
            for entity in entities
            if (command := entity.executor.select_command(*COMMANDS_OPEN))
        ]

        await self.__execute_actions(actions)

    async def batch_close_cover(self, service_call: ServiceCall) -> None:
        """Batch close selected covers."""

        entities = self.__get_entities_from_call(service_call)

        actions = [
            Action(entity.device_url, [Command(command)])
            for entity in entities
            if (command := entity.executor.select_command(*COMMANDS_CLOSE))
        ]

        await self.__execute_actions(actions)

    async def batch_stop_cover(self, service_call: ServiceCall) -> None:
        """Batch stop selected covers."""

        entities = self.__get_entities_from_call(service_call)

        actions = [
            Action(entity.device_url, [Command(command)])
            for entity in entities
            if (command := entity.executor.select_command(*COMMANDS_STOP))
        ]

        await self.__execute_actions(actions)
