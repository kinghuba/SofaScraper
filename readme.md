
# SofaScraper

  

A Python CLI tool designed to scrape and process sports match data - including statistics, lineups, incidents, and event details - directly from **sofascore.com**.

  

>**Disclaimer:** This project is intended for educational and personal research purposes only. The author is not affiliated with or endorsed by SofaScore. Use responsibly and in accordance with SofaScore's Terms of Service.

  

---

  

## Features

  

-  **Tournament Scraping** - Collect all matches for a given league and season, then scrape each with all details.

-  **Date-based Scraping** - Fetch all scheduled events for a single date, a list of dates, or a date range.

-  **Direct Match Scraping** - Scrape specific matches by providing their SofaScore URLs.

-  **Rich Match Data** - Captures statistics, lineups, incidents, scores, referee, venue, and player details via CDP network interception.

-  **Flexible Storage** - Save output locally as JSON files (per-match or per-date) or save it into database.

-  **Proxy Support** - Route requests through SOCKS/HTTP proxies for anonymity and anti-blocking.

-  **Browser Customisation** - Configure user agent, locale, and timezone to simulate real browser sessions.

  

---

  

## Installation

  

### From source (recommended for development)

  

```bash
git  clone  https://github.com/kinghuba/sofascraper.git
cd  sofascraper
```

  

**With `uv` (recommended):**

  

```bash
pip  install  uv
uv  sync

```

  

**With `pip`:**

  

```bash
pip  install  -e  .
```

  

### Install Playwright browsers

  

```bash
playwright  install  chromium
```

  

---

  

## Usage

SofaScraper exposes three CLI commands: `tournaments`, `matches`, and `dates`.
  

### Scrape tournaments

To scrape tournaments the following flags can be used:

- **--tournaments / -t** - Name, slug or ID of the tournament. (required, multiple allowed)
- **--seasons / -se** - Season ID, year or range of seasons. Allowed year/range variants ["2024";"24/25";"2024-2026";"24-26"] (optional, default: "current", multiple allowed)

**Example**
```bash
sofascraper  tournaments --sport football --tournament  premier-league  --season 24/25
sofascraper  tournaments -s football --t  679  --se 76984
sofascraper  tournaments -t 17 -t 7 -se 2024-2026
```
  

### Scrape links

To scrape match links the following flags can be used:

- **--links / -l** Sofascore links of events. (required, multiple allowed)

**Example**
```bash
sofascraper  matches -l  "https://www.sofascore.com/football/match/real-madrid-barcelona/rgbsEgb#id:15335105"
sofascraper  matches -l  "https://www.sofascore.com/football/match/arsenal-crystal-palace/hsR#id:14023963" -l https://www.sofascore.com/football/match/manchester-united-brighton-and-hove-albion/FsK#id:14023959
```

### Scrape dates

To scrape dates the following flags can be used:

- **--dates / -d** Multiple date variants are allowed: 

1. YYYY-MM-DD
2. YYYY-MM-DD,YYYY-MM-DD
3. YYYY-MM-DD-YYYY-MM-DD

**Example**

#### Single
```bash
sofascraper  dates  --sport  football  --dates  2024-11-12
```
  

#### List of dates
```bash
sofascraper  dates  --sport  football  --dates  "2024-11-12,2024-11-15"
```
  

#### Date range (no spaces around the separator)
```bash
sofascraper  dates  --sport  football  --dates  "2024-11-12-2024-12-01"
```
  

#### Named shortcuts
```bash
sofascraper  dates  --sport  football  --dates  today
sofascraper  dates  --sport  football  --dates  yesterday
sofascraper  dates  --sport  football  --dates  tomorrow
```

  

---

  

## Global Options

  

| Option | Short | Env var | Description |

|--------|-------|---------|-------------|

| `--sport` | `-s` | `SS_SPORT` | Sport to scrape (e.g. `football`) |

| `--storage` | `-st` | `SS_STORAGE` | Output format: `json` (default) or `database` |

| `--concurrency` | `-c` | `SS_CONCURRENCY` | Number of concurrent open pages` |

| `--output` | `-o` | `SS_FILE_PATH` | Root output directory (default: `data`) |

| `--proxy-url` | | `SS_PROXY_URL` | Proxy URL (e.g. `socks5://host:port`) |

| `--proxy-user` | | `SS_PROXY_USER` | Proxy username |

| `--proxy-pass` | | `SS_PROXY_PASS` | Proxy password |

| `--user-agent` | | `SS_USER_AGENT` | Custom browser user agent string |

| `--locale` | | `SS_LOCALE` | Browser locale (e.g. `en-GB`) |

| `--timezone` | | `SS_TIMEZONE` | Browser timezone ID (e.g. `Europe/London`) |

| `--headless` / `--no-headless` | | `SS_HEADLESS` | Run browser in headless mode (default: headless) |

  

---

  

## Project Structure

  

```
sofascraper/

├── cli/

  ├── cli.py # Main Click entry point

  ├── commands/

    ├── dates.py

    ├── matches.py

    └── tournaments.py

  ├── options.py

  ├── types.py

  └── validators.py

├── core/

  ├── base_scraper.py # Shared scraping logic (CDP interception, pagination)

  ├── playwright_manager.py # Playwright lifecycle management

  ├── scraper_app.py # High-level orchestrator

  └── parsers/

    ├── football_parser.py # Football data parsing

    └── tennis_parser.py # Tennis data parsing

  └── scrapers/

    └── football_scrapers.py # Football specific scraping

├── storage/

  ├── local_data_storage.py # Saving locally into JSON

  ├── pgsql_data_storage.py # Saving into Postgres database

  └── pgsql/

  ├── connection.py # Database connection

  ├── football.py # Football specific data transactions

    └── tennis.py # Tennis specific data transactions

└── utils/

  ├── browser_helpers.py # Popup handling, scrolling helpers

  ├── constants.py # URLs, browser args

  ├── enums.py

  └── dataclasses/

    ├── tennis_data_classes.py # Typed dataclasses for match data

    ├── football_data_classes.py # Typed dataclasses for match data

    └── registry_data_classes.py # Type dataclasses for registries

  ├── country_registry.py

  ├── tournament_registry.py

  └── json/

    ├── tournaments.py # Tournament data

    └── registry_data_classes.py # Country data

  ├── proxy_manager.py

  ├── setup_logging.py

  ├── position_handler.py # Handles football lineup positions

  ├── progress_tracker.py # Handling CLI visual progress tracking

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

  

## Roadmap

- [x] Database storage backend

- [ ] Tennis scraper

- [ ] Basketball scraper

- [ ] GitHub Actions CI with linting and tests

- [ ] PyPI package release

---

  

## Contributing

  

Contributions are very welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) before opening a pull request.

  

---

  

## License

  

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.