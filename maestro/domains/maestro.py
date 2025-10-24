from typing import Any

from maestro.domains.entity import Entity
from maestro.integrations.home_assistant.domain import Domain


class Maestro(Entity):
    domain = Domain.MAESTRO

    def upsert(self, state: str, attributes: dict[str, Any]) -> None:
        """Create or efficiently update a maestro domain entity"""
        self.state_manager.upsert_hass_entity(
            entity_id=self.id,
            state=state,
            attributes=attributes,
        )
