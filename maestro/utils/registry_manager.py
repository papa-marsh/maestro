import re
from datetime import timedelta
from pathlib import Path
from typing import Any, ClassVar

from structlog.stdlib import get_logger

from maestro.integrations.home_assistant.types import EntityData, EntityId
from maestro.integrations.redis import CachePrefix, RedisClient
from maestro.utils.dates import IntervalSeconds, local_now, resolve_timestamp

log = get_logger()


class RegistryManager:
    redis_client = RedisClient()

    header = "# THIS MODULE IS PROGRAMMATICALLY UPDATED - See `maestro/registry/README.md`\n\n"
    attr_import_string = "from maestro.domains.entity import EntityAttribute"
    datetime_import_string = "from datetime import datetime"
    attributes_to_ignore: ClassVar = {
        "id",
        "friendly_name",
        "last_changed",
        "last_updated",
        "previous_state",
    }

    @classmethod
    def upsert_entity(cls, entity_data: EntityData) -> None:
        """Adds or updates an entity to its respective module: maestro/registry/<domain>.py"""
        entity_id = EntityId(entity_data.entity_id)
        module_filepath = Path(f"/maestro/registry/{entity_id.domain}.py")
        cache_key = RedisClient.build_key(CachePrefix.REGISTERED, entity_id)

        if cached_value := cls.redis_client.get(key=cache_key):
            last_updated = resolve_timestamp(cached_value)
            if last_updated > local_now() - timedelta(seconds=IntervalSeconds.ONE_DAY):
                return

        try:
            if not module_filepath.exists():
                cls.write_new_module(entity_data)
            else:
                cls.update_existing_module(entity_data)

            cls.redis_client.set(
                key=cache_key,
                value=local_now().isoformat(),
                ttl_seconds=IntervalSeconds.ONE_WEEK,
            )

        except Exception:
            log.exception(f"Failed to add entity {entity_id} to registry")

    @classmethod
    def write_new_module(cls, entity_data: EntityData) -> None:
        entity_id = EntityId(entity_data.entity_id)
        module_filepath = Path(f"/maestro/registry/{entity_id.domain}.py")

        new_entry = cls._build_entry(
            entity_id=entity_id,
            attributes=entity_data.attributes,
            subclass=entity_id.domain_class_name,
            type_as_value=False,
        )
        content = (
            f"{cls.header}from maestro.domains import {entity_id.domain_class_name}\n"
            f"{cls.attr_import_string}\n{cls.datetime_import_string}\n\n{new_entry}"
        )
        module_filepath.write_text(content)
        log.info("Created new registry file", filepath=module_filepath, entity=entity_id)

    @classmethod
    def update_existing_module(cls, entity_data: EntityData) -> None:
        entity_id = EntityId(entity_data.entity_id)
        module_filepath = Path(f"/maestro/registry/{entity_id.domain}.py")

        content = module_filepath.read_text()
        lines = content.strip().split("\n")

        registered_entities = re.findall(
            pattern=r'\(["\']([^"\']*)["\'\)]',
            string=content,
        )
        if entity_id in registered_entities:
            return

        new_entry = cls._build_entry(
            entity_id=entity_id,
            attributes=entity_data.attributes,
            subclass=entity_id.domain_class_name,
            type_as_value=False,
        )

        imports = set()
        entries = [new_entry]
        current_entry: dict[str, Any] = {}
        for line in lines:
            if line.startswith("class "):
                if current_entry:
                    imports.add(current_entry["parent_class"])
                    entry_string = cls._build_entry(
                        entity_id=EntityId(current_entry["entity_id"]),
                        attributes=current_entry["attributes"],
                        subclass=current_entry["parent_class"],
                        type_as_value=True,
                    )
                    entries.append(entry_string)
                if match := re.search(r"class\s+\w+\(([^)]+)\):", line):
                    current_entry["parent_class"] = match.group(1)
                    current_entry["attributes"] = {}
            elif "EntityAttribute(" in line:
                if match := re.match(r"\s*(\w+)\s*=\s*EntityAttribute\(([^)]+)\)", line):
                    current_entry["attributes"][match.group(1)] = match.group(2)
            elif f" = {entity_id.domain_class_name}" in line:
                if match := re.match(r'\w+\s*=\s*\w+\("([^"]+)"\)', line):
                    current_entry["entity_id"] = match.group(1)

        entry_string = cls._build_entry(
            entity_id=EntityId(current_entry["entity_id"]),
            attributes=current_entry["attributes"],
            subclass=current_entry["parent_class"],
            type_as_value=True,
        )
        entries.append(entry_string)
        entries.sort()

        imports.add(current_entry["parent_class"])
        import_string = "from maestro.domains import " + ", ".join(sorted(imports))

        new_lines = [
            cls.header,
            import_string,
            cls.attr_import_string,
            cls.datetime_import_string,
            *entries,
        ]
        new_content = "\n".join(new_lines) + "\n"
        module_filepath.write_text(new_content)
        log.info("Added entity to registry", filepath=module_filepath, entity=entity_id)

    @classmethod
    def _build_entry(
        cls,
        entity_id: EntityId,
        attributes: dict,
        subclass: str | None,
        type_as_value: bool,
    ) -> str:
        pascalcase_id = "".join(word.capitalize() for word in entity_id.entity.split("_"))
        entry_class_name = entity_id.domain_class_name + pascalcase_id
        parent_class = subclass or entity_id.domain_class_name
        new_entry = f"\nclass {entry_class_name}({parent_class}):"
        attribute_added = False
        for attribute, value in attributes.items():
            if attribute not in cls.attributes_to_ignore:
                type_string = value if type_as_value else type(value).__name__
                if type_string != "NoneType":
                    new_entry += f"\n    {attribute} = EntityAttribute({type_string})"
                    attribute_added = True
        if not attribute_added:
            new_entry += " ..."
        new_entry += f'\n{entity_id.entity} = {entry_class_name}("{entity_id}")\n'

        return new_entry
