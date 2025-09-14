from pathlib import Path

from maestro.integrations.home_assistant.types import EntityId


def add_entity_to_registry(entity_id: EntityId) -> None:
    module_filepath = Path(f"scripts/registry/{entity_id.domain}.py")
    domain_class = entity_id.domain.capitalize()
    new_entity_entry = f'{entity_id.entity} = {domain_class}("{entity_id}")'

    if not module_filepath.exists():
        content = (
            "# THIS MODULE IS AUTO-GENERATED - DO NOT EDIT\n\n"
            f"from maestro.domains import {domain_class}\n\n{new_entity_entry}\n"
        )
        module_filepath.write_text(content)
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
            content = f"{import_line}\n\n" + "\n".join(sorted_entries) + "\n"
        else:
            content = (
                f"from maestro.domains import {domain_class}\n\n" + "\n".join(sorted_entries) + "\n"
            )

        module_filepath.write_text(content)
