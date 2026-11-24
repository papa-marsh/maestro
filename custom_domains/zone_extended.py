from copy import deepcopy

from maestro.domains import Zone
from maestro.integrations import EntityId, StateManager

from scripts.config.zones import ZoneMetadata, zone_metadata_registry


class ZoneExtended(Zone):
    def __init__(
        self,
        entity_id: str | EntityId,
        state_manager: StateManager | None = None,
    ):
        super().__init__(entity_id=entity_id, state_manager=state_manager)
        self._metadata: ZoneMetadata | None = None

    @property
    def metadata(self) -> ZoneMetadata:
        """Lazy-load metadata to avoid accessing state manager during module import"""
        if self._metadata is None:
            self._metadata = self.get_zone_metadata(self.entity_name)
        return self._metadata

    @classmethod
    def get_zone_metadata(cls, zone_name: str) -> ZoneMetadata:
        registry_entry = zone_metadata_registry.get(zone_name)

        zone_metadata = deepcopy(registry_entry) or ZoneMetadata()

        if zone_metadata.short_name is None:
            zone_metadata.short_name = zone_name

        return zone_metadata

    @classmethod
    def resolve_zone(cls, zone_name: str) -> Zone:
        from registry import zone as zone_registry

        for attr_name in dir(zone_registry):
            attr = getattr(zone_registry, attr_name)
            if isinstance(attr, Zone) and attr.entity_name == zone_name:
                return attr

        raise ValueError(f"No zone entity found named {zone_name}")
