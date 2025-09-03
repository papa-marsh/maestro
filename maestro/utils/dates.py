from datetime import UTC, datetime


def utc_now() -> datetime:
    return datetime.now().astimezone(UTC)


def resolve_timestamp(iso_string: str) -> datetime:
    return datetime.fromisoformat(iso_string).astimezone(UTC)
