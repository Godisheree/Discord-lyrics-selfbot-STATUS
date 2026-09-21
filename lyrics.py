import asyncio
import os
import queue
import sys
sys.stdout.reconfigure(encoding='utf-8')
import re
import requests
import threading
import time
import syncedlyrics
from datetime import datetime, timezone

from winrt.windows.media.control import (
    GlobalSystemMediaTransportControlsSessionManager as MediaManager,
    GlobalSystemMediaTransportControlsSessionPlaybackStatus
)

DISCORD_TOKEN = os.environ.get("DISCORD_TOKEN", "")
if not DISCORD_TOKEN:
    try:
        with open(os.path.join(os.path.dirname(__file__), ".env"), "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("DISCORD_TOKEN="):
                    DISCORD_TOKEN = line.split("=", 1)[1].strip()
                    break
    except OSError:
        pass
LYRIC_OFFSET = 0.65

def hide_cursor():
    sys.stdout.write("\033[?25l")
    sys.stdout.flush()

def show_cursor():
    sys.stdout.write("\033[?25h")
    sys.stdout.flush()

def clear_line_area():
    sys.stdout.write("\033[H\033[J")
    sys.stdout.flush()

def clean_lyric(text):
    if not text:
        return None

    text = text.replace("\r", "").strip()

    if "/" in text and len(text) > 40:
        return None

    if re.search(r"[a-z][A-Z][a-z]", text):
        return None

    if len(text) > 80:
        return None

    if len(re.sub(r"[a-zA-Z ]", "", text)) > len(text) * 0.4:
        return None

    return text

def fix_joined_words(text):
    if not text:
        return text
    return re.sub(r"([a-z])([A-Z])", r"\1 \2", text)

def status_text(txt):
    if not txt or re.search(r"\[(instrumental|inst|pause|interlude|music)\]", txt, re.I):
        return "\U0001F3B5"
    cleaned = fix_joined_words(clean_lyric(txt))
    return f"\U0001F3B5 {cleaned}" if cleaned else None

def trim(text, max_len=70):
    if not text:
        return text
    return text[:max_len]

def parse_lrc(lrc_string):
    lyrics = []
    if not lrc_string:
        return lyrics

    for line in lrc_string.splitlines():
        match = re.match(r'\[(\d+):(\d+(?:\.\d+)?)\]\s*(.*)', line)
        if match:
            m = int(match.group(1))
            s = float(match.group(2))
            text = match.group(3).strip()
            lyrics.append((m * 60 + s, text))

    return sorted(lyrics, key=lambda x: x[0])

session = requests.Session()

_active_song = None

def update_discord_status(text):
    url = "https://discord.com/api/v9/users/@me/settings"
    headers = {
        "authorization": DISCORD_TOKEN,
        "content-type": "application/json",
        "connection": "close"
    }

    data = (
        {"custom_status": {"text": text}} if text
        else {"custom_status": None}
    )

    try:
        session.patch(url, headers=headers, json=data, timeout=3)
    except:
        pass

_status_queue = queue.Queue()

def _status_worker():
    while True:
        snapshot, text = _status_queue.get()
        try:
            if snapshot == _active_song:
                update_discord_status(text)
        finally:
            _status_queue.task_done()

threading.Thread(target=_status_worker, daemon=True).start()

def schedule_status(text):
    _status_queue.put((_active_song, text))

_media_manager = None

async def get_media_info():
    global _media_manager
    try:
        if not _media_manager:
            _media_manager = await MediaManager.request_async()

        session = _media_manager.get_current_session()

        if session:
            playback = session.get_playback_info()
            props = await session.try_get_media_properties_async()
            timeline = session.get_timeline_properties()

            now = datetime.now(timezone.utc)
            diff = (now - timeline.last_updated_time).total_seconds()

            position = timeline.position.total_seconds() + diff
            duration = timeline.end_time.total_seconds() if timeline.end_time else None
            if duration and position > duration:
                position = duration

            return {
                "title": props.title,
                "artist": props.artist,
                "position": position,
                "duration": duration,
                "status": playback.playback_status
            }

    except:
        pass

    _media_manager = None
    return {"status": None}

def is_advertisement(title, artist):
    combined = f"{title or ''} {artist or ''}".lower()
    return "advertisement" in combined

def search_lrclib(title, artist, duration=None):
    url = "https://lrclib.net/api/search"
    params = {"track_name": title or "", "artist_name": artist or ""}

    for attempt in range(3):
        try:
            r = session.get(url, params=params, timeout=5)
            if r.status_code == 429:
                time.sleep(1)
                continue
            if not r.ok:
                return None
            tracks = r.json()
            if not tracks:
                return None

            t = (title or "").lower().strip()
            a = (artist or "").lower().strip()

            def score(c):
                s = 0
                ct = (c.get("trackName") or "").lower().strip()
                ca = (c.get("artistName") or "").lower().strip()
                if ct == t:
                    s += 2
                elif t in ct or ct in t:
                    s += 1
                if ca == a:
                    s += 2
                elif a in ca or ca in a:
                    s += 1
                if not (c.get("syncedLyrics") or "").strip():
                    s -= 10
                if duration and c.get("duration"):
                    diff = abs(c["duration"] - duration)
                    if diff < 5:
                        s += 2
                    elif diff < 15:
                        s += 1
                return s

            ranked = sorted(tracks, key=score, reverse=True)
            for c in ranked:
                synced = (c.get("syncedLyrics") or "").strip()
                if synced:
                    return synced
            return None
        except:
            time.sleep(0.5)

    return None

def search_lyrics(title, artist, duration=None):
    lrc = search_lrclib(title, artist, duration)
    if lrc:
        return lrc, "LRCLIB"

    song_id = f"{title} {artist}"
    lrc = syncedlyrics.search(
        song_id,
        providers=["Musixmatch", "NetEase", "Megalobiz", "Deezer", "Genius", "Lyricsify"]
    )
    return lrc, "Fallback"

def render(song, artist, pos, lyric):
    m, s = divmod(int(pos), 60)

    print(f"Song   : {song}")
    print(f"Artist : {artist}")
    print(f"Time   : {m:02d}:{s:02d}")
    print(f"Lyrics : {trim(lyric) if lyric else '...'}")


def get_next_lyric_index(lyrics, pos):
    for i, (t, txt) in enumerate(lyrics):
        if t > pos:
            return i
    return None

def get_current_lyric_index(lyrics, pos):
    result = None
    for i, (t, txt) in enumerate(lyrics):
        if t <= pos:
            result = i
        else:
            break
    return result

async def main_loop():
    global _active_song

    current_song = None
    current_lyrics = []
    current_line = None
    last_sent_index = -1
    status_cleared = False
    first_lyric_sent = False
    latency = 0.6

    update_discord_status(None)

    os.system("cls" if os.name == "nt" else "clear")
    hide_cursor()

    print("Detecting music...")

    try:
        while True:
            info = await get_media_info()
            status = info.get("status")

            if status == GlobalSystemMediaTransportControlsSessionPlaybackStatus.PAUSED:
                if not status_cleared:
                    status_cleared = True
                    schedule_status(None)
                current_line = None
                last_sent_index = -1
                await asyncio.sleep(1)
                continue

            if status != GlobalSystemMediaTransportControlsSessionPlaybackStatus.PLAYING:
                if not status_cleared:
                    status_cleared = True
                    schedule_status(None)
                current_line = None
                last_sent_index = -1
                await asyncio.sleep(1)
                continue

            song_id = f"{info['title']} {info['artist']}"
            raw_pos = info["position"]
            pos = raw_pos + LYRIC_OFFSET

            if song_id != current_song:
                schedule_status(None)
                current_song = song_id
                _active_song = song_id
                current_line = None
                last_sent_index = -1
                status_cleared = False
                first_lyric_sent = False

                if is_advertisement(info["title"], info["artist"]):
                    schedule_status(None)
                    status_cleared = True
                    clear_line_area()
                    render(info["title"], info["artist"], raw_pos, "(Advertisement)")
                    await asyncio.sleep(1)
                    continue

                lrc, source = await asyncio.to_thread(
                    search_lyrics,
                    info["title"],
                    info["artist"],
                    info.get("duration")
                )

                current_lyrics = parse_lrc(lrc) if lrc else []
                print(f"Source : {source}")

            if not current_lyrics:
                if not status_cleared:
                    status_cleared = True
                    current_line = None
                    last_sent_index = -1
                    schedule_status(None)
                    clear_line_area()
                    render(info["title"], info["artist"], raw_pos, "...")
                await asyncio.sleep(1)
                continue

            if current_lyrics:
                next_idx = get_next_lyric_index(current_lyrics, pos)

                if next_idx is not None and next_idx != last_sent_index:
                    next_time, next_text = current_lyrics[next_idx]
                    time_until_next = next_time - pos

                    if time_until_next <= latency and time_until_next >= 0:
                        sync_text = status_text(next_text) if next_text else "\U0001F3B5"
                        if sync_text and sync_text != current_line:
                            current_line = sync_text
                            last_sent_index = next_idx
                            if sync_text != "\U0001F3B5":
                                first_lyric_sent = True
                            schedule_status(sync_text)
                            clear_line_area()
                            render(info["title"], info["artist"], raw_pos, current_line)
                        elif not sync_text:
                            last_sent_index = next_idx

                cur_idx = get_current_lyric_index(current_lyrics, pos)
                if cur_idx is not None and last_sent_index < cur_idx:
                    _, cur_text = current_lyrics[cur_idx]
                    sync_text = status_text(cur_text) if cur_text else "\U0001F3B5"
                    if sync_text and sync_text != current_line:
                        if sync_text == "\U0001F3B5" and not first_lyric_sent:
                            last_sent_index = cur_idx
                        else:
                            current_line = sync_text
                            last_sent_index = cur_idx
                            if sync_text != "\U0001F3B5":
                                first_lyric_sent = True
                            schedule_status(sync_text)
                            clear_line_area()
                            render(info["title"], info["artist"], raw_pos, current_line)

            await asyncio.sleep(0.2)

    finally:
        show_cursor()
        update_discord_status(None)

if __name__ == "__main__":
    try:
        asyncio.run(main_loop())
    except KeyboardInterrupt:
        show_cursor()
        update_discord_status(None)
        sys.exit(0)