from datetime import datetime, timedelta, timezone


class Clock:
    _offset_seconds = 0

    @classmethod
    def now(cls) -> datetime:
        return datetime.now(timezone.utc) + timedelta(seconds=cls._offset_seconds)

    @classmethod
    def set_offset(cls, seconds: int) -> None:
        cls._offset_seconds = seconds

    @classmethod
    def advance(cls, seconds: int) -> datetime:
        cls._offset_seconds += seconds
        return cls.now()

    @classmethod
    def reset(cls) -> None:
        cls._offset_seconds = 0


def as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)
