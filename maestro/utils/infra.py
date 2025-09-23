import importlib
import re
import sys
from pathlib import Path
from typing import Any

from structlog.stdlib import get_logger

from maestro.integrations.home_assistant.types import EntityData, EntityId

log = get_logger()


def load_script_modules() -> None:
    """
    Auto-discover and import all Python modules in the scripts directory.
    This ensures that decorators like @state_change_trigger and @cron_trigger get registered.
    """
    scripts_dir = Path("/code/scripts")
    if not scripts_dir.exists():
        scripts_dir = Path.cwd() / "scripts"
    if not scripts_dir.exists():
        raise ImportError("Failed to find scripts directory while attempting to load modules")

    scripts_path = str(scripts_dir)
    if scripts_path not in sys.path:
        sys.path.insert(0, scripts_path)
        log.info("Added scripts directory to Python path", path=scripts_path)

    python_files = list(scripts_dir.rglob("*.py"))
    loaded_count = 0
    error_count = 0

    for python_file in python_files:
        if python_file.name.startswith("_") or python_file.name.startswith("test"):
            continue

        relative_path = python_file.relative_to(scripts_dir)
        module_name = str(relative_path.with_suffix("")).replace("/", ".").replace("\\", ".")

        try:
            importlib.import_module(module_name)
            log.info("Successfully loaded scripts module", module=module_name)
            loaded_count += 1
        except Exception as e:
            log.error("Failed to load scripts module", module=module_name, error=str(e))
            error_count += 1

    log.info("Script loading completed", loaded=loaded_count, errors=error_count)


def add_entity_to_registry(entity_data: EntityData) -> None:
    """This monster will add entities to maestro/registry/<domain>.py"""
    header = "# THIS MODULE IS PROGRAMMATICALLY UPDATED - See `maestro/registry/README.md`\n\n"
    attr_import_string = "from maestro.domains.entity import EntityAttribute"
    datetime_import_string = "from datetime import datetime"

    entity_id = EntityId(entity_data.entity_id)
    module_filepath = Path(f"/maestro/registry/{entity_id.domain}.py")

    attributes_to_ignore = {
        "id",
        "friendly_name",
        "last_changed",
        "last_updated",
        "previous_state",
        "test_attr",
    }

    def build_entry(
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
            if attribute not in attributes_to_ignore:
                type_string = value if type_as_value else type(value).__name__
                if type_string != "NoneType":
                    new_entry += f"\n    {attribute} = EntityAttribute({type_string})"
                    attribute_added = True
        if not attribute_added:
            new_entry += " ..."
        new_entry += f'\n{entity_id.entity} = {entry_class_name}("{entity_id}")\n'

        return new_entry

    try:
        if not module_filepath.exists():
            new_entry = build_entry(
                entity_id=entity_id,
                attributes=entity_data.attributes,
                subclass=entity_id.domain_class_name,
                type_as_value=False,
            )
            content = (
                f"{header}from maestro.domains import {entity_id.domain_class_name}\n"
                f"{attr_import_string}\n{datetime_import_string}\n\n{new_entry}"
            )
            module_filepath.write_text(content)
            log.info("Created new registry file", filepath=module_filepath, entity=entity_id)

        else:
            content = module_filepath.read_text()
            lines = content.strip().split("\n")

            registered_entities = re.findall(
                pattern=r'\(["\']([^"\']*)["\'\)]',
                string=content,
            )
            if entity_id in registered_entities:
                return

            new_entry = build_entry(
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
                        entry_string = build_entry(
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

            entry_string = build_entry(
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
                header,
                import_string,
                attr_import_string,
                datetime_import_string,
                *entries,
            ]
            new_content = "\n".join(new_lines) + "\n"
            module_filepath.write_text(new_content)
            log.info("Added entity to registry", filepath=module_filepath, entity=entity_id)

    except Exception:
        log.exception(f"Failed to add entity {entity_id} to registry")
