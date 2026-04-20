"""Click callback validators for OddsHarvester CLI."""

import re
from datetime import date, datetime, timedelta
from pathlib import Path

import click

from sofascraper.utils.sport_tournament_registry import SportTournamentRegistry


def validate_date(ctx, param, value):
    if value is None:
        return None

    value = value.strip()
    current_date = datetime.today().date()

    def parse_single(v: str) -> date:
        try:
            return datetime.strptime(v.strip(), "%Y-%m-%d").date()
        except ValueError:
            raise click.BadParameter(
                f"Invalid date '{v.strip()}'. Expected YYYY-MM-DD.",
                param=param,
            ) from None

    resolved = []

    # RANGE: YYYY-MM-DD-YYYY-MM-DD
    if len(value) == 21 and value[10] == "-":
        left, right = value[:10], value[11:]

        start = parse_single(left)
        end = parse_single(right)

        if end < start:
            raise click.BadParameter(
                f"Range end '{end}' is before start '{start}'.",
                param=param,
            )

        current = start
        while current <= end:
            resolved.append(current.isoformat())
            current += timedelta(days=1)

    elif re.fullmatch("today", value):
        resolved.append(current_date.isoformat())

    elif re.fullmatch("yesterday", value):
        current_date -= timedelta(days=1)
        resolved.append(current_date.isoformat())

    elif re.fullmatch("tomorrow", value):
        current_date += timedelta(days=1)
        resolved.append(current_date.isoformat())

    elif "," in value or (value.startswith("[") and value.endswith("]")):
        if value.startswith("[") and value.endswith("]"):
            value = value[1:-1]

        parts = [p.strip() for p in value.split(",") if p.strip()]

        if not parts:
            raise click.BadParameter("Date list is empty.", param=param)

        resolved = [parse_single(p).isoformat() for p in parts]

    # SINGLE DATE
    else:
        resolved = [parse_single(value).isoformat()]

    return sorted(set(resolved))


def validate_season(ctx, param, value):
    if not value:
        return None

    results = []

    for season in value:
        season = season.strip()

        if re.fullmatch("all", season):
            return ["all"]

        if re.match(r"^\d{5,}$", season):
            season = SportTournamentRegistry.get_by_season_id(int(season))

            if season:
                season_id = season["id"]

            if not season_id:
                raise click.BadParameter(
                    f"Invalid season '{season_id}'. Season id could not be found in the database.",
                    param=param,
                )

            results.append(season_id)
            continue

        def _parse_single(v: str) -> str:
            v = v.strip()

            # Match "2024"
            if re.fullmatch(r"\d{4}", v):
                return v

            # Match "24/25"
            if re.fullmatch(r"\d{2}/\d{2}", v):
                start, end = map(int, v.split("/"))
                if end != (start + 1) % 100:
                    raise click.BadParameter(
                        f"Invalid season '{v}'. Expected consecutive years like '24/25'.",
                        param=param,
                    )
                return v

            raise click.BadParameter(
                f"Invalid season '{v}'. Expected 'YYYY' or 'YY/YY'.",
                param=param,
            )

        # RANGE: 2024-2026 or 24-26
        if "-" in season and "," not in season:
            parts = season.split("-")
            if len(parts) == 2:
                left, right = parts[0].strip(), parts[1].strip()

                # YYYY-YYYY
                if re.fullmatch(r"\d{4}", left) and re.fullmatch(r"\d{4}", right):
                    if int(right) < int(left):
                        raise click.BadParameter(
                            f"Range end '{right}' is before start '{left}'.",
                            param=param,
                        )
                    for r in list(range(int(left), int(right) + 1)):
                        results.append(str(r))
                    continue

                # YY-YY
                if re.fullmatch(r"\d{2}", left) and re.fullmatch(r"\d{2}", right):
                    if int(right) < int(left):
                        raise click.BadParameter(
                            f"Range end '{right}' is before start '{left}'.",
                            param=param,
                        )
                    for r in list(range(int(left), int(right) + 1)):
                        results.append(str(r))
                    continue

            raise click.BadParameter(
                f"Invalid range '{season}'. Expected 'YYYY-YYYY' or 'YY-YY'.",
                param=param,
            )

        # [2024, 24/25] or 2024,24/25
        if season.startswith("[") and season.endswith("]"):
            season = season[1:-1]

        if "," in season:
            parts = [p.strip() for p in season.split(",") if p.strip()]
            if not parts:
                raise click.BadParameter("Season list is empty.", param=param)

            for part in parts:
                part = _parse_single(part)
                results.append(part)

            continue

        # --- SINGLE
        results.append(_parse_single(season))
        continue

    return results


def validate_tournament(ctx, param, value):
    if not value:
        return None

    results = []

    # Handle it as list of items
    for tournament in value:
        if bool(re.fullmatch(r"\d+", tournament)):
            results.append(_validate_tournament_data(tournament_id=int(tournament)).get("slug"))
        elif bool(re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", tournament)):
            results.append(_validate_tournament_data(slug=tournament).get("slug"))
        else:
            results.append(_validate_tournament_data(name=tournament).get("slug"))

    return results


def _validate_tournament_data(
    tournament_id: int | None = None,
    slug: str | None = None,
    name: str | None = None,
) -> dict:

    result = None
    tournament = SportTournamentRegistry()
    slug = slug.strip() if slug else slug
    name = name.strip() if name else name

    if tournament_id is not None:
        result = tournament.get_by_id(tournament_id)

    if result is None and slug is not None:
        result = tournament.get_by_slug(slug)

    if result is None and name is not None:
        result = tournament.get_by_name(name)

    if result is None:
        raise click.BadParameter(
            f"Tournament not found (id={tournament_id}, slug={slug}, name={name})",
            param_hint="'--tournament'",
        )

    return result


def validate_proxy_url(ctx, param, value):
    if not value:
        return None

    proxy_pattern = re.compile(r"^(?P<scheme>https?|socks5|socks4)://(?P<host>[\\w\\.-]+):(?P<port>\\d+)$")

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

    path = Path(value)

    if ".." in path.parts:
        raise click.BadParameter(
            f"Output path must not contain '..' segments: '{value}'",
            param_hint="'--output'",
        )

    if path.exists() and not path.is_dir():
        raise click.BadParameter(
            f"Output path must be a directory: '{value}'",
            param_hint="'--output'",
        )

    return value
