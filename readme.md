# SofaScraper

A Python CLI tool designed to scrape and process sports match data - including statistics, lineups, incidents, and event details - directly from SofaScore.

> ⚠️ **Disclaimer:** This project is intended for educational and personal research purposes only. The author is not affiliated with or endorsed by SofaScore. Use responsibly and in accordance with SofaScore's Terms of Service.

---

## Features

- **Tournament Scraping** - Collect all matches for a given league and season, then scrape each with all details.
- **Date-based Scraping** - Fetch all scheduled events for a single date, a list of dates, or a date range.
- **Direct Match Scraping** - Scrape specific matches by providing their SofaScore URLs.
- **Rich Match Data** - Captures statistics, lineups, incidents, scores, referee, venue, and player details via CDP network interception.
- **Flexible Storage** - Save output locally as JSON files (per-match or per-date). Database support is planned.
- **Proxy Support** - Route requests through SOCKS/HTTP proxies for anonymity and anti-blocking.
- **Browser Customisation** - Configure user agent, locale, and timezone to simulate real browser sessions.
- **Docker-ready** - Ships with Docker-optimised Playwright browser arguments for headless container environments.

---

## Installation

### From source (recommended for development)

```bash
git clone https://github.com/kinghuba/sofascraper.git
cd sofascraper
```

**With `uv` (recommended):**

```bash
pip install uv
uv sync
```

**With `pip`:**

```bash
pip install -e .
```

### Install Playwright browsers

```bash
playwright install chromium
```

---

## Usage

SofaScraper exposes three CLI commands: `tournaments`, `matches`, and `dates`.

### Scrape a tournament

```bash
sofascraper tournaments \
  --sport football \
  -tournaments premier-league \
  -season 24/25 \
  --headless
```

### Scrape specific match links

```bash
sofascraper matches \
  --sport football \
  -links "https://www.sofascore.com/football/match/real-madrid-barcelona/rgbsEgb#id:15335105" \
  --headless
```

### Scrape by date

```bash
# Single date
sofascraper dates --sport football -dates 2024-11-12

# List of dates
sofascraper dates --sport football -dates "2024-11-12,2024-11-15"

# Date range
sofascraper dates --sport football -dates "2024-11-12 - 2024-12-01"
```

---

## Global Options

| Option | Short | Description |
|--------|-------|-------------|
| `--sport` | `-s` | Sport to scrape (e.g. `football`) |
| `--storage-format` | | Output format: `json` (default) or `db` |
| `--file-path` | | Root output directory (default: `data`) |
| `--proxy-url` | | Proxy URL (e.g. `socks5://host:port`) |
| `--proxy-user` | | Proxy username |
| `--proxy-pass` | | Proxy password |
| `--browser-user-agent` | | Custom browser user agent string |
| `--browser-locale` | | Browser locale (e.g. `en-GB`) |
| `--browser-timezone` | | Browser timezone ID (e.g. `Europe/London`) |
| `--headless` | | Run browser in headless mode |
| `--verbose` / `--quiet` | `-v` / `-q` | Increase or suppress log output |

---

## Project Structure

```
sofascraper/
├── cli/
│   ├── cli.py                  # Main Click entry point
│   ├── commands/
│   │   ├── dates.py
│   │   ├── matches.py
│   │   └── tournaments.py
│   ├── options.py
│   ├── types.py
│   └── validators.py
├── core/
│   ├── base_scraper.py         # Shared scraping logic (CDP interception, pagination)
│   ├── playwright_manager.py   # Playwright lifecycle management
│   ├── scraper_app.py          # High-level orchestrator
│   ├── url_builder.py          # SofaScore URL construction
│   └── football/
│       ├── football_scraper.py # Football-specific scraping workflows
│       └── football_parser.py  # Football data parsing
├── storage/
│   └── local_data_storage.py   # JSON file storage
└── utils/
    ├── browser_helpers.py       # Popup handling, scrolling helpers
    ├── constants.py             # URLs, browser args
    ├── country_registry.py
    ├── enums.py                 # CommandEnum, Sport, StorageFormat
    ├── football_data_classes.py # Typed dataclasses for match data
    ├── proxy_manager.py
    ├── setup_logging.py
    ├── sport_season_registry.py
    ├── sport_tournament_registry.py
    └── utils.py
```

---

## Output Format

Each scraped match is saved as an individual JSON file (named by match ID), or the matches are grouped for a date (named by date) inside the configured output directory.

Date-based scraping saves one JSON file per date containing all events for that day.

A typical match JSON contains:

```json
{
  "match_id": 12345678,
  "match_url": "https://www.sofascore.com/...",
  "base": { "id": 12345678, "slug": "...", "status": {}, "home_team": {}, "away_team": {}, ... },
  "statistics": [ { "period": "ALL", "groups": [ { "group_name": "Possession", "statistics": [...] } ] } ],
  "incidents": [ { "id": 1, "incident_type": "goal", "time": 23, "is_home": true, ... } ],
  "lineups": { "confirmed": true, "home_formation": "4-3-3", "home_players": [...], ... }
}
```

---

## Docker

Docker support is included for headless, containerised scraping. Build the image from the project root:

```bash
docker build -t sofascraper:local .
```

Then run a scraping command:

```bash
docker run --rm sofascraper:local \
  sofascraper dates --sport football -dates 2024-11-12 --headless
```

The Docker build uses the `PLAYWRIGHT_BROWSER_ARGS_DOCKER` constants (no sandbox, GPU disabled) defined in `utils/constants.py`.

---

## Roadmap

- [ ] Database storage backend
- [ ] Tennis scraper
- [ ] Basketball scraper
- [ ] CSV export
- [ ] GitHub Actions CI with linting and tests
- [ ] PyPI package release

---

## Contributing

Contributions are very welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) before opening a pull request.

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.