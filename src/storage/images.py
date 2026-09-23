"""Photo downloads."""

from __future__ import annotations

from pathlib import Path

from playwright.sync_api import BrowserContext

from src.utils.logger import log
from src.utils.text import sanitize_filename
from src.utils.urls import guess_ext, upsize_image_url


def download_images(listings: list, images_dir: Path, context: BrowserContext) -> None:
    images_dir.mkdir(parents=True, exist_ok=True)
    for l in listings:
        if not l.images:
            continue
        folder = images_dir / sanitize_filename(l.id or l.title[:40])
        folder.mkdir(parents=True, exist_ok=True)
        for i, src in enumerate(l.images, start=1):
            dest = folder / f"{i:02d}{guess_ext(src)}"
            if dest.exists():
                continue
            try:
                resp = context.request.get(upsize_image_url(src), timeout=20000)
                if resp.ok:
                    dest.write_bytes(resp.body())
                else:
                    resp = context.request.get(src, timeout=20000)
                    if resp.ok:
                        dest.write_bytes(resp.body())
            except Exception as exc:
                log(f"    could not download {src}: {exc}")
