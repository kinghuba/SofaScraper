"""Custom Click parameter types"""

import click


class StorageFormat(click.Choice):
    """Allowed storage/output formats."""

    def __init__(self):
        super().__init__(["json", "database"], case_sensitive=False)


STORAGE_FORMAT = StorageFormat()
