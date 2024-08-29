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


def ping():
    if not ARCHIVEBOX_ENDPOINT:
        log.error(
            "Archivebox config incomplete or missing, set "
            "`ARCHIVEBOX_ENDPOINT` via env var!"
        )
        return

    # test connection on startup
    for retry in range(1, 5):
        # if not ARCHIVEBOX_ENDPOINT or not ARCHIVEBOX_TOKEN:
        # log.error(
        #     "Archivebox config incomplete or missing, set "
        #     "`ARCHIVEBOX_ENDPOINT` and `ARCHIVEBOX_TOKEN` via env var!"
        # )
        try:
            res = requests.head(ARCHIVEBOX_ENDPOINT)
            if res.ok:
                return
            res.raise_for_status()
        except Exception as e:
            log.warn(
                f"`{e}` while connecting to `{ARCHIVEBOX_ENDPOINT}: retrying ..."
            )
        # res = requests.post(
        #     f"{ARCHIVEBOX_ENDPOINT}/api/v1/auth/check_api_token",
        #     json={"token": ARCHIVEBOX_TOKEN},
        # )
        # if res.ok and res.json()["success"]:
        #     pass
        time.sleep(retry**2)

    # give up
    res = requests.head(ARCHIVEBOX_ENDPOINT)
    if res.ok:
        return
    log.error(res.text)
    log.error(
        f"ArchiveBox {ARCHIVEBOX_ENDPOINT} not reachable or credentials "
        "not authorized, check `ARCHIVEBOX_ENDPOINT` and "
        "`ARCHIVEBOX_TOKEN` env vars!"
    )


ping()


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
            "archive_methods": [
                "favicon",
                "headers",
                "pdf",
                "screenshot",
                "wget",
                "title",
                "htmltotext",
            ],
        },
    )


@anycache
def archive(url: str):
    res = _archive(url)
    for retry in range(3):
        if res.ok:
            log.info(f"Archived `{url}")
            return datetime.now(UTC).isoformat()
        else:
            log.warning(f"Archive error: `{res.text}`, retrying ...")
            time.sleep(retry**5)
    log.error(f"Maximum retries exceeded for url `{url}`")


async def request(flow: HTTPFlow):
    if ARCHIVEBOX_ENDPOINT is None or ARCHIVEBOX_TOKEN is None:
        return
    url = flow.request.url
    loop = asyncio.get_running_loop()
    loop.run_in_executor(None, archive, url)
