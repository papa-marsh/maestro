import importlib
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
        if python_file.name.startswith("_") or "tests" in str(python_file):
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
    domain_class = "".join(word.capitalize() for word in entity_id.domain.split("_"))
    new_entity_entry = f'{entity_id.entity} = {domain_class}("{entity_id}")'
    header = "# THIS MODULE IS PROGRAMMATICALLY UPDATED - EDIT WITH CAUTION\n\n"

    try:
        if not module_filepath.exists():
            content = f"{header}from maestro.domains import {domain_class}\n\n{new_entity_entry}\n"
            module_filepath.write_text(content)
            log.info("Created new registry file", filepath=module_filepath, entity=entity_id)
        else:
            content = module_filepath.read_text()
            lines = content.strip().split("\n")
            entity_entries = set()

            import_line = None
            for line in lines:
                line = line.strip()
                if line.startswith("from maestro.domains import"):
                    import_line = line
                elif line and "=" in line and not line.startswith("#"):
                    entity_entries.add(line)

            entity_entries.add(new_entity_entry)
            sorted_entries = sorted(entity_entries)

            if import_line:
                content = f"{header}{import_line}\n\n" + "\n".join(sorted_entries) + "\n"
            else:
                content = (
                    f"{header}from maestro.domains import {domain_class}\n\n"
                    f"{'\n'.join(sorted_entries)}\n"
                )

            module_filepath.write_text(content)
            log.info("Added entity to registry", filepath=module_filepath, entity=entity_id)
    except Exception:
        log.exception(f"Failed to add entity {entity_id} to registry")
