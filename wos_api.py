import aiohttp
import asyncio
import logging
import os
import json
from bs4 import BeautifulSoup
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# simple in-memory cache: player_id -> (data, expires_at)
_cache = {}
CACHE_TTL = timedelta(seconds=60)


async def _get_json_or_text(session, url, headers=None, timeout=15):
    try:
        async with session.get(url, headers=headers, timeout=timeout) as r:
            text = await r.text()
            # try parse JSON
            try:
                return r.status, await r.json(content_type=None)
            except Exception:
                return r.status, text
    except Exception as e:
        raise


async def fetch_player_info(player_id: str) -> dict:
    """Try to get player info from wos-giftcode site.

    Returns a dict with keys like { 'id', 'name', 'level', 'alliance', ... }
    or raises Exception on failure.
    """
    now = datetime.utcnow()
    # cache check
    entry = _cache.get(player_id)
    if entry and entry[1] > now:
        return entry[0]

    base = "https://wos-giftcode.centurygame.com"
    headers = {
        "User-Agent": "WhiteoutBot/1.0 (+https://example/)",
        "Accept": "application/json, text/html, */*;q=0.8",
        "Referer": base,
    }

    # VIP endpoint support: some sites expose a callback API that requires a token header
    vip_base = "https://cg-vip-mall-wos.centurygame.com"
    vip_token = os.getenv('WOS_TOKEN')
    vip_auth = os.getenv('WOS_AUTH')
    if vip_token or vip_auth:
        vip_headers = headers.copy()
        if vip_token:
            vip_headers['token'] = vip_token
        vip_headers['Origin'] = 'https://store.centurygames.com'
        vip_headers['Referer'] = 'https://store.centurygames.com/'
        vip_url = vip_base + '/api/callback/get_role_info'
        payload = {
            "game_id": "20121",
            "role_id": player_id,
            "ts": int(datetime.utcnow().timestamp()),
            "webVersion": "v1.6.0",
            "language_code": "EN",
            "auth": vip_auth or "",
        }
        try:
            timeout = aiohttp.ClientTimeout(total=20)
            async with aiohttp.ClientSession(timeout=timeout) as vip_sess:
                async with vip_sess.post(vip_url, json=payload, headers=vip_headers) as vip_resp:
                    text = await vip_resp.text()
                    if vip_resp.status == 200:
                        try:
                            body = await vip_resp.json()
                        except Exception:
                            body = None
                        if isinstance(body, dict):
                            data = _normalize_role_json(body, player_id, vip_url)
                            _cache[player_id] = (data, now + CACHE_TTL)
                            return data
                        # fallback: try parse HTML returned
                        if isinstance(text, str) and text:
                            parsed = _parse_player_html(text, player_id, source_url=vip_url)
                            if parsed:
                                _cache[player_id] = (parsed, now + CACHE_TTL)
                                return parsed
                    else:
                        logger.debug(f"VIP endpoint {vip_url} returned status {vip_resp.status}")
        except Exception as e:
            logger.debug(f"VIP endpoint probe failed: {e}")

    timeout = aiohttp.ClientTimeout(total=20)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        # 1) Try common JSON/API endpoints first (probe)
        api_candidates = [
            f"{base}/api/player/{player_id}",
            f"{base}/api/players/{player_id}",
            f"{base}/player/{player_id}.json",
            f"{base}/player/{player_id}",
        ]
        for url in api_candidates:
            try:
                status, body = await _get_json_or_text(session, url, headers=headers)
            except Exception as e:
                logger.debug(f"probe {url} failed: {e}")
                continue
            if status == 200:
                # if JSON returned, normalize
                if isinstance(body, dict):
                    data = _normalize_player_json(body, player_id, url)
                    _cache[player_id] = (data, now + CACHE_TTL)
                    return data
                # if HTML returned, parse below
                html = body if isinstance(body, str) else None
                if html:
                    parsed = _parse_player_html(html, player_id, source_url=url)
                    if parsed:
                        _cache[player_id] = (parsed, now + CACHE_TTL)
                        return parsed

        # 2) fallback: fetch the player page directly and parse html
        try:
            page_url = f"{base}/player/{player_id}"
            status, body = await _get_json_or_text(session, page_url, headers=headers)
            if status == 200:
                html = body if isinstance(body, str) else None
                if html:
                    parsed = _parse_player_html(html, player_id, source_url=page_url)
                    if parsed:
                        _cache[player_id] = (parsed, now + CACHE_TTL)
                        return parsed
                elif isinstance(body, dict):
                    data = _normalize_player_json(body, player_id, page_url)
                    _cache[player_id] = (data, now + CACHE_TTL)
                    return data
            raise Exception(f"Player page returned status {status}")
        except Exception as e:
            logger.error(f"Failed to fetch player info for {player_id}: {e}")
            raise


def _normalize_player_json(obj: dict, player_id: str, source_url: str) -> dict:
    # Map likely fields — adapt after inspecting the real API JSON keys
    return {
        "id": obj.get("id") or player_id,
        "name": obj.get("name") or obj.get("nickname") or obj.get("playerName"),
        "level": obj.get("level") or obj.get("lv") or None,
        "power": obj.get("power") or obj.get("combat_power") or None,
        "alliance": obj.get("alliance") or obj.get("guild") or None,
        "raw": obj,
        "source": source_url,
    }


def _find_in_dict(obj, keys):
    """Recursively search for any of the keys in a nested dict and return value or None."""
    if not obj or not isinstance(obj, (dict, list)):
        return None
    if isinstance(obj, dict):
        for k in keys:
            if k in obj:
                return obj[k]
        for v in obj.values():
            if isinstance(v, (dict, list)):
                found = _find_in_dict(v, keys)
                if found is not None:
                    return found
    elif isinstance(obj, list):
        for item in obj:
            found = _find_in_dict(item, keys)
            if found is not None:
                return found
    return None


def _normalize_role_json(obj: dict, player_id: str, source_url: str) -> dict:
    """Normalize JSON returned by the VIP/get_role_info endpoint into the standard shape."""
    # common candidate keys
    name = _find_in_dict(obj, ("name", "nickname", "nick", "playerName", "role_name"))
    level = _find_in_dict(obj, ("level", "lv", "power_level"))
    power = _find_in_dict(obj, ("power", "combat_power", "fight", "battle_power"))
    alliance = _find_in_dict(obj, ("alliance", "guild", "clan", "union", "guild_name"))

    # try to coerce numeric fields
    def to_int(x):
        try:
            return int(x)
        except Exception:
            try:
                return int(float(x))
            except Exception:
                return None

    return {
        "id": str(_find_in_dict(obj, ("role_id", "id", "player_id")) or player_id),
        "name": name,
        "level": to_int(level),
        "power": to_int(power),
        "alliance": alliance,
        "raw": obj,
        "source": source_url,
    }


def _parse_player_html(html: str, player_id: str, source_url: str = None) -> dict:
    """Lightweight HTML parsing — update selectors after inspecting actual page."""
    try:
        soup = BeautifulSoup(html, "html.parser")
        # Example selectors — adjust to actual page markup
        name_el = soup.select_one(".player-name") or soup.select_one("h1.player") or soup.select_one(".nickname")
        level_el = soup.select_one(".player-level") or soup.find(text=lambda t: t and "Level" in t)
        power_el = soup.select_one(".player-power") or soup.find(text=lambda t: t and "Power" in t)
        alliance_el = soup.select_one(".player-alliance") or soup.select_one(".guild-name")

        def clean_text(el):
            if not el:
                return None
            if hasattr(el, 'get_text'):
                return el.get_text(strip=True)
            return str(el).strip()

        data = {
            "id": player_id,
            "name": clean_text(name_el),
            "level": clean_text(level_el),
            "power": clean_text(power_el),
            "alliance": clean_text(alliance_el),
            "source": source_url,
        }
        return data
    except Exception as e:
        logger.debug(f"HTML parse failed: {e}")
        return None
