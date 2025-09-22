import importlib
import re
import sys
from pathlib import Path

from structlog.stdlib import get_logger

from maestro.integrations.home_assistant.types import EntityId

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


def add_entity_to_registry(entity_id: EntityId) -> None:
    module_filepath = Path(f"/maestro/registry/{entity_id.domain}.py")
    new_entity_entry = f'{entity_id.entity} = {entity_id.domain_class_name}("{entity_id}")'
    header = """
    # THIS MODULE IS PROGRAMMATICALLY UPDATED - EDIT WITH CAUTION\n\n
    # - Each entity must exist on exactly one line.\n
    # - Base domain classes can be replaced by subclasses:\n
    #       eg. `TeslaClimate(<car_entity>)` instead of `Climate(<car_entity>)`.\n
    # - Protip: Comment out unused entities to remove them from IDE autocomplete.\n\n\n
    """

    try:
        if not module_filepath.exists():
            content = (
                f"{header}from maestro.domains import {entity_id.domain_class_name}"
                f"\n\n{new_entity_entry}\n"
            )
            module_filepath.write_text(content)
            log.info("Created new registry file", filepath=module_filepath, entity=entity_id)

        else:
            content = module_filepath.read_text()
            registered_entities = re.findall(
                pattern=r'\(["\']([^"\']*)["\'\)]',
                string=content,
            )
            if entity_id in registered_entities:
                return

            lines = content.strip().split("\n")
            new_lines = [header, ""] if header not in content else []
            entity_entries = set()
            for line in lines:
                if " = " in line:
                    entity_entries.add(line)
                else:
                    new_lines.append(line)

            entity_entries.add(new_entity_entry)
            new_lines.extend(sorted(entity_entries))

            new_content = "\n".join(new_lines) + "\n"
            module_filepath.write_text(new_content)
            log.info("Added entity to registry", filepath=module_filepath, entity=entity_id)

    except Exception:
        log.exception(f"Failed to add entity {entity_id} to registry")
