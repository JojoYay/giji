# 会議 文字起こし・議事録生成ツール / Meeting Transcription & Minutes Generator

> [English version below](#english)

---

## 日本語

Google Gemini API を使って、会議の音声・動画ファイルから **文字起こし** と **議事録（要約）** を自動生成するツールです。Streamlit による Web UI とコマンドライン (CLI) の両方で利用できます。

### 主な機能

- 音声/動画ファイルから Gemini API で文字起こし
- 文字起こし結果から議事録（要約）を自動生成
- 動画ファイルは自動で音声のみ抽出（ffmpeg）してアップロードサイズを削減
- Streamlit Web UI でファイル選択・設定・結果確認が可能
- 503/429 エラー時の自動リトライ機能
- `.env` ファイルで API キーを安全に管理

### 必要なもの

- **Python 3.10+**
- **Google Gemini API キー** — [Google AI Studio](https://aistudio.google.com/apikey) から取得
- **ffmpeg**（任意） — 動画から音声抽出に使用。なくても音声ファイルはそのまま処理可能

### インストール

```bash
# リポジトリをクローン
git clone https://github.com/JojoYay/giji.git
cd giji

# 依存パッケージをインストール
pip install -r requirements.txt

# ffmpeg 同梱バイナリも利用可能（オプション）
pip install imageio-ffmpeg

# .env ファイルを作成して API キーを設定
cp .env.example .env
# .env を編集して GEMINI_API_KEY=あなたのAPIキー に書き換え
```

### 使い方

#### Web UI（Streamlit）

```bash
streamlit run app.py
```

または `start.bat` をダブルクリック。

ブラウザが開いたら：
1. サイドバーで API キー・出力先フォルダ・ファイル名を設定
2. 音声/動画ファイルをアップロード
3. 「▶ 文字起こし・要約 開始」ボタンをクリック
4. 結果をタブで確認・ダウンロード

#### コマンドライン (CLI)

```bash
# 基本
python gemini_transcribe_v2.py --file "会議録音.mp4"

# オプション指定
python gemini_transcribe_v2.py \
  --file "会議録音.mp4" \
  --model gemini-2.5-flash \
  --output_dir output \
  --output_prefix "2024-04-14_定例会議"
```

### 出力ファイル

| ファイル | 内容 |
|---|---|
| `{プレフィックス}_transcript.txt` | タイムスタンプ付き文字起こし |
| `{プレフィックス}_minutes.md` | 議事録（Markdown形式） |

### 対応ファイル形式

mp4, m4a, wav, mp3, webm, ogg, flac, mkv, avi, mov

### プロジェクト構成

```
├── app.py                    # Streamlit Web UI
├── gemini_transcribe_v2.py   # コアロジック (CLI対応)
├── start.bat                 # Windows起動用バッチ
├── requirements.txt          # 依存パッケージ
├── .env.example              # 環境変数テンプレート
└── .gitignore
```

---

<a name="english"></a>

## English

Automatically generate **transcriptions** and **meeting minutes (summaries)** from audio/video files using the Google Gemini API. Available as both a Streamlit Web UI and a command-line tool.

### Features

- Transcribe audio/video files using the Gemini API
- Auto-generate structured meeting minutes from transcriptions
- Auto-extract audio from video files (via ffmpeg) to reduce upload size
- Streamlit Web UI with file upload, settings, and result preview
- Auto-retry on 503/429 server errors
- Secure API key management via `.env` file

### Prerequisites

- **Python 3.10+**
- **Google Gemini API key** — Get one at [Google AI Studio](https://aistudio.google.com/apikey)
- **ffmpeg** (optional) — Used for extracting audio from video files. Audio files work without it.

### Installation

```bash
# Clone the repository
git clone https://github.com/JojoYay/giji.git
cd giji

# Install dependencies
pip install -r requirements.txt

# Optional: install bundled ffmpeg binary
pip install imageio-ffmpeg

# Create .env file and set your API key
cp .env.example .env
# Edit .env and set GEMINI_API_KEY=your_actual_api_key
```

### Usage

#### Web UI (Streamlit)

```bash
streamlit run app.py
```

Or double-click `start.bat` on Windows.

Once the browser opens:
1. Configure API key, output folder, and filename in the sidebar
2. Upload an audio/video file
3. Click "▶ Start Transcription"
4. View and download results in tabs

#### Command Line (CLI)

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

### Output Files

| File | Description |
|---|---|
| `{prefix}_transcript.txt` | Timestamped transcription |
| `{prefix}_minutes.md` | Meeting minutes (Markdown) |

### Supported File Formats

mp4, m4a, wav, mp3, webm, ogg, flac, mkv, avi, mov

### Project Structure

```
├── app.py                    # Streamlit Web UI
├── gemini_transcribe_v2.py   # Core logic (also works as CLI)
├── start.bat                 # Windows launcher
├── requirements.txt          # Python dependencies
├── .env.example              # Environment variable template
└── .gitignore
```

### License

MIT
