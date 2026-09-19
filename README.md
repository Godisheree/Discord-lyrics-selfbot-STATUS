# Discord Lyrics Status

A Python script that syncs the lyrics of whatever song you're currently playing on Windows (Spotify, YouTube, any app with a Windows media session) to your Discord custom status — in sync with the music.

It reads the current track and playback position straight from the Windows media API (SMTC), pulls timestamped LRC lyrics, and pre-fires the Discord status update just before each lyric change so the status lands as the line actually begins.

## Features

- Detects any playing track via the Windows Media Transport Controls API — no Spotify webhook or plugin needed.
- Fetches synced (LRC) lyrics automatically — LRCLIB first, then a multi-provider fallback.
- Pre-fire scheduling with latency compensation for near-zero-delay lyric changes.
- Instrumental breaks render as 🎵 instead of freezing on the last lyric line.
- Waits for the first real lyric before showing any break, so a song switch never opens with a stale 🎵.
- Auto-clears status on pause / stop / unknown player.
- Skips Spotify advertisements.
- Cleans up noisy lyric lines (joined words, junk metadata).

## Requirements

- Windows 10/11 (media session API required)
- Python 3.8+
- Your Discord user token

## Setup

1. Clone this repository:
   ```bash
   git clone https://github.com/Godisheree/Discord-lyrics-selfbot-STATUS.git
   cd Discord-lyrics-selfbot-STATUS
   ```

2. Install the required packages:
   ```bash
   pip install -r requirements.txt
   ```

3. Add your Discord token — either as an environment variable:
   ```bash
   set DISCORD_TOKEN=your_token_here
   ```
   Or create a `.env` file in the repo root (`lyrics.py` loads it automatically):
   ```
   DISCORD_TOKEN=your_token_here
   ```
   The `.env` route is recommended.

   **How to get your token:**
   - Open Discord web in your browser and press F12.
   - Go to the **Network** tab and filter by `/api`.
   - Trigger a request, click the request, and look under **Request Headers** for the `authorization` field. That's your token. Don't share it with anyone.

4. Run it:
   ```bash
   python lyrics.py
   ```

## Configuration

Configuration lives at the top of `lyrics.py`:

- `LYRIC_OFFSET` (seconds) — compensates for the request round-trip to Discord's API. Default `0.65`. Bump it up if lyrics feel late on your machine, down if they feel early.

There's also a `latency` value (`latency = 0.6`) inside `main_loop()` — how far ahead of each lyric line the request fires — tuned as a pair with `LYRIC_OFFSET`.

## Notes

- The status shown is Discord's **custom status** (under your username), not the profile bio.
- Lyrics come from LRCLIB or a fallback provider, so sync quality varies by track — some tracks simply don't have accurate timestamps.

## Disclaimer

This is a selfbot and goes against Discord's Terms of Service. You can be banned for using it. Use at your own risk.