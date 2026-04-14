# 📝 Meeting Transcription & Minutes Generator

**[日本語版 README はこちら → README_ja.md](README_ja.md)**

Automatically generate **transcriptions** and **meeting minutes (summaries)** from audio/video files using the Google Gemini API. Available as both a Streamlit Web UI and a command-line tool.

## Features

- 🎤 Transcribe audio/video files using the Gemini API
- 📋 Auto-generate structured meeting minutes from transcriptions
- 🎬 Auto-extract audio from video files (via ffmpeg) to reduce upload size
- 🖥️ Streamlit Web UI with file upload, settings, and result preview
- 💰 Real-time token usage tracking and API cost reporting (USD)
- 🔄 Auto-retry on 503/429 server errors
- 🔐 Secure API key management via `.env` file

## Prerequisites

| Requirement | Details |
|-------------|---------|
| **Python** | 3.10+ |
| **Gemini API key** | Get one free at [Google AI Studio](https://aistudio.google.com/apikey) |
| **ffmpeg** (optional) | For audio extraction from video. `pip install imageio-ffmpeg` also works |

## Installation

```bash
# 1. Clone the repository
git clone https://github.com/JojoYay/giji.git
cd giji

# 2. Install dependencies
pip install -r requirements.txt

# 3. Optional: install bundled ffmpeg binary
pip install imageio-ffmpeg

# 4. Create .env file and set your API key
cp .env.example .env
# Edit .env and set GEMINI_API_KEY=your_actual_api_key
```

## Usage

### Web UI (Streamlit) — Recommended

```bash
streamlit run app.py
```

On Windows, you can also double-click **`start.bat`**.

Once the browser opens:

1. Configure **API key**, **model**, **output folder**, and **filename** in the sidebar
2. **Upload** an audio/video file
3. Click **"▶ Start Transcription"**
4. View results in tabs once the progress bar completes
5. 💰 Check the **cost report** for token usage and charges (USD)
6. Download results via the download buttons

### Command Line (CLI)

```bash
# Basic usage
python gemini_transcribe_v2.py --file "meeting.mp4"

# With options
python gemini_transcribe_v2.py \
  --file "meeting.mp4" \
  --model gemini-2.5-flash \
  --output_dir output \
  --output_prefix "2024-04-14_weekly"
```

A cost report is displayed after each run:

```
==================================================
💰 API Usage & Cost Report
==================================================
  Model: gemini-2.5-flash
  Input rate: $1.00 / 1M tokens
  Output rate: $2.50 / 1M tokens
--------------------------------------------------
  [Transcription]
    Input: 520,000 tokens
    Output: 15,000 tokens
  [Minutes Generation]
    Input: 16,000 tokens
    Output: 2,500 tokens
--------------------------------------------------
  Total input: 536,000 tokens
  Total output: 17,500 tokens
--------------------------------------------------
  Input cost: $0.5360
  Output cost: $0.0438
  ★ Total cost: $0.5798 USD
==================================================
```

## Output Files

| File | Description |
|---|---|
| `{prefix}_transcript.txt` | Timestamped transcription with speaker labels |
| `{prefix}_minutes.md` | Meeting minutes (Markdown format) |

## Supported File Formats

`mp4` `m4a` `wav` `mp3` `webm` `ogg` `flac` `mkv` `avi` `mov`

## API Pricing Reference

| Model | Input (text) | Input (audio) | Output |
|-------|-------------|---------------|--------|
| gemini-2.5-flash | $0.30/1M | $1.00/1M | $2.50/1M |
| gemini-2.5-pro | $1.25/1M | $1.25/1M | $10.00/1M |

※ Prices as of April 2026. See [Gemini API Pricing](https://ai.google.dev/gemini-api/docs/pricing) for latest.

## Project Structure

```
├── app.py                    # Streamlit Web UI
├── gemini_transcribe_v2.py   # Core logic (also works as CLI)
├── start.bat                 # Windows launcher
├── requirements.txt          # Python dependencies
├── .env.example              # Environment variable template
└── .gitignore
```

## License

MIT
