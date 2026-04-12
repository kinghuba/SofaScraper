"""Custom Click parameter types"""

import click


class CommaList(click.ParamType):
    """Accept a comma-separated string and return it as a list of stripped items."""

    name = "COMMA_LIST"

    def convert(self, value, param, ctx):
        if value is None:
            return None
        if isinstance(value, list):
            return value
        return [v.strip() for v in value.split(",") if v.strip()]


class StorageFormat(click.Choice):
    """Allowed storage/output formats."""

    def __init__(self):
        super().__init__(["json", "database"], case_sensitive=False)


COMMA_LIST = CommaList()
STORAGE_FORMAT = StorageFormat()
