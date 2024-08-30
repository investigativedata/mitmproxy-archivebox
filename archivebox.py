"""
https://docs.mitmproxy.org/stable/addons-overview/

The commented lines are for current archivebox:dev and use the WIP api
The uncommented lines rely on the public post endpoint, which means that
`PUBLIC_ADD_VIEW=True` is required for the ArchiveBox deployment.
"""

from datetime import datetime, UTC
import asyncio
import os
import logging
import time
import requests
from mitmproxy.http import HTTPFlow
from anystore.decorators import anycache


log = logging.getLogger(__name__)

ARCHIVEBOX_ENDPOINT = os.environ.get("ARCHIVEBOX_ENDPOINT", "").rstrip("/")
ARCHIVEBOX_TOKEN = os.environ.get("ARCHIVEBOX_TOKEN")
ARCHIVEBOX_METHODS = os.environ.get(
    "ARCHIVEBOX_METHODS",
    "favicon,headers,pdf,screenshot,wget,title,htmltotext,archive_org",
).split(",")
ARCHIVE_REQUEST_METHODS = os.environ.get("ARCHIVE_REQUEST_METHODS", "GET").split(",")


if not ARCHIVEBOX_ENDPOINT:
    log.error(
        "Archivebox config incomplete or missing, set "
        "`ARCHIVEBOX_ENDPOINT` via env var!"
    )

# test connection on startup
# if not ARCHIVEBOX_ENDPOINT or not ARCHIVEBOX_TOKEN:
# log.error(
#     "Archivebox config incomplete or missing, set "
#     "`ARCHIVEBOX_ENDPOINT` and `ARCHIVEBOX_TOKEN` via env var!"
# )
try:
    res = requests.head(ARCHIVEBOX_ENDPOINT)
    res.raise_for_status()
except Exception as e:
    log.error(f"`{e}` while connecting to `{ARCHIVEBOX_ENDPOINT}`.")
# res = requests.post(
#     f"{ARCHIVEBOX_ENDPOINT}/api/v1/auth/check_api_token",
#     json={"token": ARCHIVEBOX_TOKEN},
# )
# if res.ok and res.json()["success"]:
#     pass


def _archive(url: str) -> requests.Response:
    s = requests.Session()
    # s.get(f"{ARCHIVEBOX_ENDPOINT}/api/v1/docs")  # set cookie FIXME
    s.get(f"{ARCHIVEBOX_ENDPOINT}/add/")  # set cookie FIXME
    # headers = {
    #     "X-ArchiveBox-API-Key": ARCHIVEBOX_TOKEN,
    #     "X-CSRFToken": s.cookies.get("csrftoken"),
    # }
    # archive_url = f"{ARCHIVEBOX_ENDPOINT}/api/v1/cli/add"
    archive_url = f"{ARCHIVEBOX_ENDPOINT}/add/"
    return s.post(
        archive_url,
        data={
            "url": url,
            "parser": "auto",
            "depth": "0",
            "tags": "",
            "archive_methods": ARCHIVEBOX_METHODS,
        },
    )


@anycache
def archive(url: str):
    for retry in range(3):
        res = _archive(url)
        if res.ok:
            log.info(f"Archived `{url}")
            return datetime.now(UTC).isoformat()
        else:
            log.warning(f"Archive error: `{res.text}`, retrying ...")
            time.sleep(retry**5)
    log.error(f"Maximum retries exceeded for url `{url}`")


async def request(flow: HTTPFlow):
    if flow.request.method in ARCHIVE_REQUEST_METHODS:
        url = flow.request.url
        loop = asyncio.get_running_loop()
        loop.run_in_executor(None, archive, url)
