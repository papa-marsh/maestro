from datetime import UTC, datetime


def resolve_timestamp(iso_string: str) -> datetime:
    return datetime.fromisoformat(iso_string).astimezone(UTC)
