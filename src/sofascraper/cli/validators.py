"""Click callback validators for OddsHarvester CLI."""

from datetime import datetime
import re
from typing import List, Optional

import click

import sofascraper.utils.sport_tournament_registry as SportTournamentRegistry
from sofascraper.utils.sport_season_registry import SportSeasonRegistry


def validate_date(ctx, param, value):
    """
    Validate the --date argument. Accepts:
      - Single date:   "2022-11-12"
      - List:          ["2022-11-12", "2022-11-15", "2022-11-19"]
      - Range:         "2022-11-12 - 2022-12-01"
    """
    if value is None:
        return None

    def _parse_single(v: str) -> None:
        try:
            datetime.strptime(v.strip(), "%Y-%m-%d")
        except ValueError:
            raise click.BadParameter(
                f"Invalid date '{v.strip()}'. Expected YYYY-MM-DD (e.g., 2025-02-27).",
                param=param,
            ) from None

    value = value.strip()

    # "2022-11-12 - 2022-12-01"
    if " - " in value:
        parts = value.split(" - ", 1)
        if len(parts) != 2:
            raise click.BadParameter(
                f"Invalid range '{value}'. Expected 'YYYY-MM-DD - YYYY-MM-DD'.",
                param=param,
            )
        start_str, end_str = parts
        _parse_single(start_str)
        _parse_single(end_str)

        start = datetime.strptime(start_str.strip(), "%Y-%m-%d")
        end = datetime.strptime(end_str.strip(), "%Y-%m-%d")
        if end < start:
            raise click.BadParameter(
                f"Range end '{end_str.strip()}' is before start '{start_str.strip()}'.",
                param=param,
            )
        return value

    # "[2022-11-12, 2022-11-15]" or "2022-11-12, 2022-11-15"
    if value.startswith("[") and value.endswith("]"):
        value = value[1:-1]

    if "," in value:
        parts = [p.strip() for p in value.split(",") if p.strip()]
        if not parts:
            raise click.BadParameter("Date list is empty.", param=param)
        for part in parts:
            _parse_single(part)
        return value

    # Single date
    _parse_single(value)
    return value


def validate_season(ctx, param, value):
    if not value:
        return None

    results = []

    for item in value:
        if "=" not in item:
            raise click.BadParameter(
                "Invalid format for season. Use id= or name=",
                param_hint="'--season'",
            )

        key, raw_vals = item.split("=", 1)
        values = raw_vals.split(",")

        for v in values:
            if key == "id":
                res = validate_season_data(season_id=int(v))
            elif key == "name":
                res = validate_season_data(name=v)
            else:
                raise click.BadParameter(
                    f"Unsupported season filter: {key}",
                    param_hint="'--season'",
                )

            results.append(res)

    return results


def validate_season_data(
    season_id: Optional[int] = None,
    name: Optional[str] = None,
    tournament_id: Optional[int] = None,
) -> dict:
    if not any([season_id, name]):
        raise click.BadParameter(
            "You must provide at least season_id or name",
            param_hint="'--season'",
        )

    seasons = SportSeasonRegistry.all_flat()

    result = None

    if season_id is not None:
        result = next((s for s in seasons if s["id"] == season_id), None)

    elif name is not None:
        result = next((s for s in seasons if s["year"] == name), None)

    if result is None:
        raise click.BadParameter(
            f"Season not found (id={season_id}, name={name})",
            param_hint="'--season'",
        )

    if tournament_id is not None and result["tournament_id"] != tournament_id:
        raise click.BadParameter(
            f"Season {result['id']} does not belong to tournament {tournament_id}",
            param_hint="'--season'",
        )

    return result


def validate_tournament(ctx, param, value):
    if not value:
        return None

    results = []

    for item in value:
        if "=" not in item:
            raise click.BadParameter(
                "Invalid format for tournament. Use id=, slug=, or name=",
                param_hint="'--tournament'",
            )

        key, raw_vals = item.split("=", 1)
        values = raw_vals.split(",")

        for v in values:
            if key == "id":
                res = validate_tournament_data(tournament_id=int(v))
            elif key == "slug":
                res = validate_tournament_data(slug=v)
            elif key == "name":
                res = validate_tournament_data(name=v)
            else:
                raise click.BadParameter(
                    f"Unsupported tournament filter: {key}",
                    param_hint="'--tournament'",
                )

            results.append(res)

    return results


def validate_tournament_data(
    tournament_id: int | None = None,
    slug: str | None = None,
    name: str | None = None,
) -> dict:

    if not any([tournament_id, slug, name]):
        raise click.BadParameter(
            "Provide at least one of: tournament_id, slug, name",
            param_hint="'--tournament'",
        )

    result = None

    if tournament_id is not None:
        result = SportTournamentRegistry.get_by_id(tournament_id)

    elif slug is not None:
        result = SportTournamentRegistry.get_by_slug(slug)

    elif name is not None:
        result = SportTournamentRegistry.get_by_name(name)

    if result is None:
        raise click.BadParameter(
            f"Tournament not found (id={tournament_id}, slug={slug}, name={name})",
            param_hint="'--tournament'",
        )

    return result


def validate_proxy_url(ctx, param, value):
    if not value:
        return None

    proxy_pattern = re.compile(
        r"^(?P<scheme>https?|socks5|socks4)://(?P<host>[\\w\\.-]+):(?P<port>\\d+)$"
    )

    if not proxy_pattern.match(value):
        raise click.BadParameter(
            f"Invalid proxy URL '{value}'. Expected format: 'http[s]://host:port' or 'socks5://host:port'",
            param_hint="'--proxy-url'",
        )

    return value


def validate_concurrency(ctx, param, value):
    if value is not None and value <= 0:
        raise click.BadParameter(
            "Concurrency must be a positive integer.",
            param_hint="'--concurrency'",
        )
    return value


def validate_file_path(ctx, param, value):
    if value is None:
        return None

    from pathlib import Path

    path = Path(value)

    if ".." in path.parts:
        raise click.BadParameter(
            f"Output path must not contain '..' segments: '{value}'",
            param_hint="'--output'",
        )

    if path.exists() and path.is_dir():
        raise click.BadParameter(
            f"Output path must not be an existing directory: '{value}'",
            param_hint="'--output'",
        )

    return value
