import os
import re
import time

import yt_dlp
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

load_dotenv()

app = FastAPI(title="NoxMusic Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# okru_id -> (direct_url, expiry_time)
_cache: dict[str, tuple[str, float]] = {}
CACHE_SECONDS = 20 * 60


def resolve_okru(okru_id: str) -> str:
    cached = _cache.get(okru_id)
    if cached and cached[1] > time.time():
        return cached[0]

    opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        # audio ke liye sabse chhota mp4, data bachta hai
        "format": "worst[ext=mp4]/worst",
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(f"https://ok.ru/video/{okru_id}", download=False)

    url = info.get("url")
    if not url:
        raise ValueError("Direct URL nahi mila")

    _cache[okru_id] = (url, time.time() + CACHE_SECONDS)
    return url


@app.get("/")
def root():
    return {"status": "ok", "app": "NoxMusic Backend"}


@app.get("/health")
def health():
    return {"status": "alive"}


@app.get("/stream/{okru_id}")
def stream(okru_id: str):
    if not re.fullmatch(r"\d{6,20}", okru_id):
        raise HTTPException(status_code=400, detail="Invalid OK.ru video id")
    try:
        direct_url = resolve_okru(okru_id)
    except Exception as e:
        _cache.pop(okru_id, None)
        raise HTTPException(status_code=502, detail=f"OK.ru resolve failed: {e}")
    return RedirectResponse(direct_url, status_code=302)
