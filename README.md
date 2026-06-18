# 🎵 Discord Lyrics Selfbot Status

Real-time synced lyrics on your Discord custom status. Automatically detects whatever music you're playing on Windows (Spotify, YouTube Music, etc.) and updates your Discord status with the current lyric line — perfectly in sync.

![Python](https://img.shields.io/badge/Python-3.8+-blue?logo=python&logoColor=white)
![Windows](https://img.shields.io/badge/Windows-10%2F11-0078D6?logo=windows&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green)

## ✨ Features

- 🎧 **Auto-detect music** — hooks into Windows Media API to see what's playing
- 📝 **Synced lyrics** — fetches time-synced lyrics (LRC format) from NetEase
- ⚡ **Pre-fire scheduling** — sends API requests *before* the lyric changes, compensating for network latency so your status updates at the exact right moment
- 🧹 **Auto-clear** — clears your status when music is paused or stopped
- 📊 **Terminal dashboard** — clean live display showing current song, artist, time, and lyric
- 🔧 **Auto latency calibration** — measures your actual ping to Discord API on startup for precise sync

## 📋 Requirements

- **Windows 10 or 11** (uses Windows Media Transport API)
- **Python 3.8+** — [Download here](https://www.python.org/downloads/)
- **Discord user token**

## 🚀 Setup

### 1. Clone the repository

```bash
git clone https://github.com/Godisheree/Discord-lyrics-selfbot-STATUS.git
cd Discord-lyrics-selfbot-STATUS
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure your Discord token

Open `lyrics.py` and paste your Discord token into the `DISCORD_TOKEN` variable:

```python
DISCORD_TOKEN = "your_token_here"
```

<details>
<summary><b>🔑 How to get your Discord token</b></summary>

1. Open [Discord Web](https://discord.com/app) in your browser and log in.
2. Press **F12** to open Developer Tools.
3. Go to the **Network** tab.
4. Type **`/api`** in the filter box.
5. Click on any channel/server in Discord to trigger a request.
6. Click on one of the requests that appear (e.g. `science` or `messages`).
7. In the **Headers** tab, scroll down to **Request Headers**.
8. Find the **`authorization`** field — that's your token.

> ⚠️ **Never share your token with anyone.** It gives full access to your account.

</details>

### 4. Run the script

```bash
python lyrics.py
```

Play a song on Spotify (or any media player) and watch your Discord status update in real-time! 🎶

## ⚙️ Configuration

You can tweak these values at the top of `lyrics.py`:

| Variable | Default | Description |
|---|---|---|
| `DISCORD_TOKEN` | `""` | Your Discord user token |
| `LYRIC_OFFSET` | `0.45` | Fine-tune lyric timing (seconds). Increase if lyrics feel late, decrease if too early |

## 🛠️ How it works

Unlike traditional approaches that detect a lyric change *then* send the update (reactive), this script uses **pre-fire scheduling**:

```
Traditional:  Lyric changes → Detect → Send request → Delay appears ❌
This script:  Know next lyric timestamp → Send request early → Arrives on time ✅
```

1. On startup, the script **measures your actual ping** to the Discord API (average of 3 requests).
2. While music plays, the script **looks ahead** — it knows when the next lyric line will appear.
3. It fires the API request **`latency` seconds before** the lyric timestamp.
4. The request arrives at Discord **exactly when the lyric changes** in the song.

## 📝 License

[MIT License](LICENSE)

## ⚠️ Disclaimer

This is a **selfbot** — it automates actions on your personal Discord account using your user token. This is against [Discord's Terms of Service](https://discord.com/terms). Use at your own risk.
