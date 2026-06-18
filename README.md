# Discord Lyrics Status

A simple Python script to automatically sync the lyrics of the song you're currently playing on Windows (like Spotify) directly to your Discord custom status. 

I modified this to be completely zero-delay. It uses a pre-fire scheduling method so the status updates exactly when the lyric changes in the song.

## Features

- Auto-detects music from Windows Media API.
- Fetches LRC synced lyrics automatically.
- Pre-fire latency compensation (zero delay sync).
- Auto-clears status when music pauses.

## Requirements

- Windows 10 or 11
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

3. Add your token to `lyrics.py`:
   Open `lyrics.py` and put your Discord token in the `DISCORD_TOKEN` variable:
   ```python
   DISCORD_TOKEN = "your_token_here"
   ```

   **How to get your token:**
   - Open Discord Web in your browser and press F12.
   - Go to the Network tab and type `/api` in the filter.
   - Click around in Discord to trigger a request, then click on it in the network tab.
   - Look under Request Headers for the `authorization` field. That's your token. Don't share this with anyone.

4. Run it:
   ```bash
   python lyrics.py
   ```

## Configuration

Inside `lyrics.py`, there is a `LYRIC_OFFSET` variable (default `0.45`). You can adjust this value to fine-tune the delay if the lyrics feel slightly out of sync on your machine.

## Disclaimer

This is a selfbot and goes against Discord's Terms of Service. Use it at your own risk.
