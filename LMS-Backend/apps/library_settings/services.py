from django.db import transaction

from apps.library_settings.models import LibrarySettings


def get_settings() -> LibrarySettings:
    return LibrarySettings.load()


@transaction.atomic
def update_settings(data: dict, actor=None) -> LibrarySettings:
    settings = LibrarySettings.load()
    working_hours = data.pop("working_hours", None)
    for field, value in data.items():
        setattr(settings, field, value)
    if working_hours:
        settings.working_hours_open = working_hours["open"]
        settings.working_hours_close = working_hours["close"]
    settings.updated_by = actor
    settings.save()
    return settings
