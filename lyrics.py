import asyncio
import os
import sys
sys.stdout.reconfigure(encoding='utf-8')
import re
import requests
import syncedlyrics
from datetime import datetime, timezone

from winrt.windows.media.control import (
    GlobalSystemMediaTransportControlsSessionManager as MediaManager,
    GlobalSystemMediaTransportControlsSessionPlaybackStatus
)

DISCORD_TOKEN = ""  # Paste your Discord token here
LYRIC_OFFSET = 0.45 # Kompensasi khusus sebesar 450ms untuk menutupi sisa delay pengiriman ke API Discord

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

def update_discord_status(text):
    url = "https://discord.com/api/v9/users/@me/settings"
    headers = {
        "authorization": DISCORD_TOKEN,
        "content-type": "application/json"
    }

    data = (
        {"custom_status": {"text": text}} if text
        else {"custom_status": None}
    )

    try:
        session.patch(url, headers=headers, json=data, timeout=5)
    except:
        pass

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

            return {
                "title": props.title,
                "artist": props.artist,
                "position": timeline.position.total_seconds() + diff,
                "status": playback.playback_status
            }

    except:
        pass

    return {"status": None}

def render(song, artist, pos, lyric):
    m, s = divmod(int(pos), 60)

    print(f"Song   : {song}")
    print(f"Artist : {artist}")
    print(f"Time   : {m:02d}:{s:02d}")
    print(f"Lyrics : {trim(lyric) if lyric else '...'}")


API_LATENCY = 0.25  # Estimasi waktu (detik) yang dibutuhkan request HTTP sampai ke Discord

def measure_api_latency():
    """Mengukur latency aktual ke Discord API saat startup (rata-rata dari beberapa ping)."""
    import time
    url = "https://discord.com/api/v9/users/@me/settings"
    headers = {
        "authorization": DISCORD_TOKEN,
        "content-type": "application/json"
    }
    results = []
    for i in range(4):
        try:
            start = time.perf_counter()
            session.patch(url, headers=headers, json={"custom_status": None}, timeout=5)
            elapsed = time.perf_counter() - start
            if i > 0:  # Buang pengukuran pertama (cold start SSL)
                results.append(elapsed)
        except:
            pass
    if results:
        return sum(results) / len(results)
    return API_LATENCY

def get_next_lyric_index(lyrics, pos):
    """Cari index lirik berikutnya yang belum muncul."""
    for i, (t, txt) in enumerate(lyrics):
        if t > pos:
            return i
    return None

def get_current_lyric_index(lyrics, pos):
    """Cari index lirik yang sedang aktif."""
    result = None
    for i, (t, txt) in enumerate(lyrics):
        if t <= pos:
            result = i
        else:
            break
    return result

async def main_loop():
    current_song = None
    current_lyrics = []
    current_line = None
    last_sent_index = -1

    # Ukur latency aktual ke Discord API
    print("Mengukur latency ke Discord API...")
    latency = await asyncio.to_thread(measure_api_latency)
    print(f"Latency terukur: {latency*1000:.0f}ms")

    update_discord_status(None)

    os.system("cls" if os.name == "nt" else "clear")
    hide_cursor()

    print("Detecting music...")

    try:
        while True:
            info = await get_media_info()
            status = info.get("status")

            if status == GlobalSystemMediaTransportControlsSessionPlaybackStatus.PAUSED:
                update_discord_status(None)
                current_line = None
                last_sent_index = -1
                await asyncio.sleep(1)
                continue

            if status != GlobalSystemMediaTransportControlsSessionPlaybackStatus.PLAYING:
                update_discord_status(None)
                current_line = None
                last_sent_index = -1
                await asyncio.sleep(1)
                continue

            song_id = f"{info['title']} {info['artist']}"

            if song_id != current_song:
                current_song = song_id
                current_line = None
                last_sent_index = -1

                lrc = await asyncio.to_thread(
                    syncedlyrics.search,
                    song_id,
                    providers=["NetEase"]
                )

                current_lyrics = parse_lrc(lrc) if lrc else []

            pos = info["position"]

            if current_lyrics:
                # Cek lirik berikutnya dan kirim request LEBIH AWAL
                next_idx = get_next_lyric_index(current_lyrics, pos)

                if next_idx is not None and next_idx != last_sent_index:
                    next_time, next_text = current_lyrics[next_idx]
                    time_until_next = next_time - pos

                    # Kirim request 'latency' detik SEBELUM lirik muncul
                    # sehingga request tiba di Discord tepat saat lirik berganti
                    if time_until_next <= latency and time_until_next >= 0:
                        cleaned = fix_joined_words(clean_lyric(next_text))
                        if cleaned and cleaned != current_line:
                            current_line = cleaned
                            last_sent_index = next_idx
                            asyncio.create_task(
                                asyncio.to_thread(
                                    update_discord_status,
                                    f"🎵 {current_line}"
                                )
                            )
                            clear_line_area()
                            render(info["title"], info["artist"], pos, current_line)
                        elif not cleaned:
                            # Lirik tidak valid, skip ke berikutnya
                            last_sent_index = next_idx

                # Juga handle lirik saat ini (untuk kasus pertama kali / seek)
                cur_idx = get_current_lyric_index(current_lyrics, pos)
                if cur_idx is not None and last_sent_index < cur_idx:
                    _, cur_text = current_lyrics[cur_idx]
                    cleaned = fix_joined_words(clean_lyric(cur_text))
                    if cleaned and cleaned != current_line:
                        current_line = cleaned
                        last_sent_index = cur_idx
                        asyncio.create_task(
                            asyncio.to_thread(
                                update_discord_status,
                                f"🎵 {current_line}"
                            )
                        )
                        clear_line_area()
                        render(info["title"], info["artist"], pos, current_line)

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
