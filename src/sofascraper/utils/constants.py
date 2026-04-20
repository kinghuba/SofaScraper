SOFASCORE_BASE_URL = "https://www.sofascore.com"

PLAYWRIGHT_BROWSER_ARGS = [
    "--disable-background-networking",
    "--disable-extensions",
    "--mute-audio",
    "--window-size=1280,720",
    "--disable-popup-blocking",
    "--disable-translate",
    "--no-first-run",
    "--disable-infobars",
    "--disable-features=IsolateOrigins,site-per-process",
    "--enable-gpu-rasterization",
    "--disable-blink-features=AutomationControlled",
]

PLAYWRIGHT_BROWSER_ARGS_DOCKER = [
    "--disable-dev-shm-usage",
    "--no-sandbox",
    "--headless",
    "--disable-gpu",
    "--disable-background-networking",
    "--disable-popup-blocking",
    "--disable-extensions",
    "--disable-blink-features=AutomationControlled",
    "--disable-features=IsolateOrigins,site-per-process",
    "--mute-audio",
    "--window-size=1280,720",
]

WANTED_SUFFIXES = {
    "football": [
        "/lineups",
        "/statistics",
        "/incidents",
        "",
        "/managers",
        "/comments",
        "/shotmap",
        "/graph",
        "/odds/1/featured",
    ],
    "tennis": ["", "/statistics", "/odds/1/featured", "/tennis-power", "/point-by-point"],
}

POPUP_TIMEOUT_MS = 5_000
GOTO_TIMEOUT_MS = 5_000
