# 📝 会議 文字起こし・議事録生成ツール

Google Gemini API を使って、会議の音声・動画ファイルから **文字起こし** と **議事録（要約）** を自動生成するツールです。  
Streamlit による Web UI とコマンドライン (CLI) の両方で利用できます。

## 主な機能

- 🎤 音声/動画ファイルから Gemini API で文字起こし
- 📋 文字起こし結果から議事録（要約）を自動生成
- 🎬 動画ファイルは自動で音声のみ抽出（ffmpeg）してアップロードサイズを削減
- 🖥️ Streamlit Web UI でファイル選択・設定・結果確認が可能
- 💰 消費トークン数と API 利用料金（USD）をリアルタイム表示
- 🔄 503/429 エラー時の自動リトライ機能
- 🔐 `.env` ファイルで API キーを安全に管理

## 必要なもの

| 項目 | 説明 |
|------|------|
| **Python** | 3.10 以上 |
| **Gemini API キー** | [Google AI Studio](https://aistudio.google.com/apikey) から無料取得 |
| **ffmpeg**（任意） | 動画から音声抽出に使用。`pip install imageio-ffmpeg` で同梱版も利用可 |

## インストール

```bash
# 1. リポジトリをクローン
git clone https://github.com/JojoYay/giji.git
cd giji

# 2. 依存パッケージをインストール
pip install -r requirements.txt

# 3. ffmpeg 同梱バイナリも利用可能（オプション）
pip install imageio-ffmpeg

# 4. .env ファイルを作成して API キーを設定
cp .env.example .env
# .env を開いて GEMINI_API_KEY=あなたのAPIキー に書き換え
```

## 使い方

### Web UI（Streamlit）— おすすめ

```bash
streamlit run app.py
```

Windows の場合は **`start.bat`** をダブルクリックでも起動できます。

ブラウザが開いたら：

1. **サイドバー** で API キー・モデル・出力先フォルダ・ファイル名を設定
2. 音声/動画ファイルを **アップロード**
3. **「▶ 文字起こし・要約 開始」** ボタンをクリック
4. 進捗バーが完了したら、結果をタブで確認
5. 💰 **コストレポート** でトークン消費量と料金(USD)を確認
6. ダウンロードボタンでファイルを保存

### コマンドライン (CLI)

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

CLI でも実行後にコストレポートが表示されます：

```
==================================================
💰 API使用量・コストレポート
==================================================
  モデル: gemini-2.5-flash
  入力単価: $1.00 / 1M tokens
  出力単価: $2.50 / 1M tokens
--------------------------------------------------
  [文字起こし]
    入力: 520,000 tokens
    出力: 15,000 tokens
  [議事録生成]
    入力: 16,000 tokens
    出力: 2,500 tokens
--------------------------------------------------
  合計入力: 536,000 tokens
  合計出力: 17,500 tokens
--------------------------------------------------
  入力コスト: $0.5360
  出力コスト: $0.0438
  ★ 合計コスト: $0.5798 USD
==================================================
```

## 出力ファイル

| ファイル | 内容 |
|---|---|
| `{プレフィックス}_transcript.txt` | タイムスタンプ・話者付き文字起こし |
| `{プレフィックス}_minutes.md` | 議事録（Markdown 形式） |

## 対応ファイル形式

`mp4` `m4a` `wav` `mp3` `webm` `ogg` `flac` `mkv` `avi` `mov`

## API 料金（参考）

| モデル | 入力 (テキスト) | 入力 (音声) | 出力 |
|--------|----------------|-------------|------|
| gemini-2.5-flash | $0.30/1M | $1.00/1M | $2.50/1M |
| gemini-2.5-pro | $1.25/1M | $1.25/1M | $10.00/1M |

※ 料金は 2026年4月時点の情報です。最新は [Gemini API Pricing](https://ai.google.dev/gemini-api/docs/pricing) を参照。

## プロジェクト構成

```
├── app.py                    # Streamlit Web UI
├── gemini_transcribe_v2.py   # コアロジック (CLI対応)
├── start.bat                 # Windows起動用バッチ
├── requirements.txt          # 依存パッケージ
├── .env.example              # 環境変数テンプレート
└── .gitignore
```

## ライセンス

MIT
