import os
import re
import time

import requests
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

OK_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Referer": "https://ok.ru/",
    "Origin": "https://ok.ru",
}

# audio ke liye sabse chhoti quality pehle
QUALITY_ORDER = ["mobile", "lowest", "low", "sd", "hd", "full"]

_cache: dict[str, tuple[str, float]] = {}
CACHE_SECONDS = 20 * 60


def fetch_metadata(okru_id: str) -> dict:
    r = requests.post(
        "https://ok.ru/dk",
        data={"cmd": "videoPlayerMetadata", "mid": okru_id},
        headers=OK_HEADERS,
        timeout=20,
    )
    r.raise_for_status()
    data = r.json()
    if isinstance(data, dict) and data.get("error"):
        raise ValueError(f"OK.ru error: {data.get('error')}")
    return data


def resolve_okru(okru_id: str) -> str:
    cached = _cache.get(okru_id)
    if cached and cached[1] > time.time():
        return cached[0]

    data = fetch_metadata(okru_id)
    by_name = {v.get("name"): v.get("url") for v in data.get("videos", []) if v.get("url")}

    url = next((by_name[n] for n in QUALITY_ORDER if n in by_name), None)
    if not url:
        url = data.get("hlsManifestUrl") or data.get("hlsMasterPlaylistUrl")
    if not url:
        raise ValueError("Koi playable URL nahi mila (video private/blocked ho sakta hai)")

    _cache[okru_id] = (url, time.time() + CACHE_SECONDS)
    return url


@app.get("/")
def root():
    return {"status": "ok", "app": "NoxMusic Backend"}


@app.get("/health")
def health():
    return {"status": "alive"}


@app.get("/info/{okru_id}")
def info(okru_id: str):
    """Debug: dekho OK.ru kaunsi qualities de raha hai."""
    if not re.fullmatch(r"\d{6,20}", okru_id):
        raise HTTPException(status_code=400, detail="Invalid OK.ru video id")
    try:
        data = fetch_metadata(okru_id)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))
    return {
        "qualities": [v.get("name") for v in data.get("videos", [])],
        "has_hls": bool(data.get("hlsManifestUrl") or data.get("hlsMasterPlaylistUrl")),
    }


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
